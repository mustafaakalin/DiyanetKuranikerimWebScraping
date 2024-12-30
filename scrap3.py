import requests
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import time

"""Arapça metinlerin doğru şekilde işlenmesi ve hataların ele alınması için aşağıdaki güncellenmiş kodu hazırladım. Bu yapı, her bir istekte hata oluştuğunda yeniden denemeyi içerir ve yalnızca Arapça ayetleri çeker."""


BASE_URL = "https://kuran.diyanet.gov.tr"
SURE_URL_TEMPLATE = "https://kuran.diyanet.gov.tr/tefsir/sure/{}"

def fetch_url_with_retries(url, retries=3, delay=2):
    """Belirtilen URL'yi hata durumunda yeniden denemelerle al."""
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(delay)  # Yeniden denemeden önce bekle
            else:
                print(f"URL çekilemedi: {url}, Hata: {e}")
    return None

def get_sure_data(sure_id):
    """Bir sureye ait bilgileri çek."""
    url = SURE_URL_TEMPLATE.format(sure_id)
    response = fetch_url_with_retries(url)
    if not response:
        return {"sure_id": sure_id, "hakkinda": None, "nuzul": None, "konusu": None, "fazileti": None, "ayet_links": []}
    
    soup = BeautifulSoup(response.content, 'html.parser')
    sure_data = {"sure_id": sure_id}
    try:
        sure_data['hakkinda'] = soup.find("div", class_="bs-callout bs-callout-default text-justify").text.strip()
        sure_data['nuzul'] = soup.find("div", class_="bs-callout bs-callout-info text-justify").text.strip()
        sure_data['konusu'] = soup.find("div", class_="bs-callout bs-callout-primary text-justify").text.strip()
        sure_data['fazileti'] = soup.find("div", class_="bs-callout bs-callout-success text-justify").text.strip()
    except AttributeError:
        pass
    
    # Ayet bağlantıları
    ayet_links = soup.find("div", class_="panel-body").find_all("a", href=True)
    sure_data['ayet_links'] = [BASE_URL + link['href'] for link in ayet_links]
    return sure_data

def get_arabic_ayet(ayet_url):
    """Bir ayetin sadece Arapça metnini çek."""
    response = fetch_url_with_retries(ayet_url)
    if not response:
        return {"ayet_url": ayet_url, "ayet": None}
    
    soup = BeautifulSoup(response.content, 'html.parser')
    ayet_data = {"ayet_url": ayet_url}
    try:
        ayet_data['ayet'] = soup.find("div", class_="alert alert-info").text.strip()
    except AttributeError:
        pass
    
    return ayet_data

def fetch_sure_and_arabic_ayet_data(sure_ids):
    """Sure ve ayet verilerini eş zamanlı çek."""
    sure_list = []
    ayet_list = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        # Sure bilgilerini paralel olarak çek
        sure_results = list(tqdm(executor.map(get_sure_data, sure_ids), total=len(sure_ids), desc="Sureler Çekiliyor"))
        sure_list.extend(sure_results)
        
        # Tüm ayet bağlantılarını topla
        all_ayet_links = []
        for sure in sure_results:
            all_ayet_links.extend(sure.get('ayet_links', []))
        
        # Sadece Arapça ayetleri paralel olarak çek
        ayet_results = list(tqdm(executor.map(get_arabic_ayet, all_ayet_links), total=len(all_ayet_links), desc="Ayetler Çekiliyor"))
        ayet_list.extend(ayet_results)

    return sure_list, ayet_list

# Sure ve Ayet Verilerini Topla
sure_ids = range(1, 115)  # 1'den 114'e kadar sure ID'leri
sure_list, ayet_list = fetch_sure_and_arabic_ayet_data(sure_ids)

# Verileri CSV'ye Kaydet
sure_df = pd.DataFrame(sure_list)
ayet_df = pd.DataFrame(ayet_list)

# Arapça metinlerin düzgün kaydedilmesi için utf-8-sig kodlaması kullan
sure_df.to_csv("sureler3.csv", index=False, encoding='utf-8-sig')
ayet_df.to_csv("arapca_ayetler3.csv", index=False, encoding='utf-8-sig')
