import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import time

def correct_arabic_numbers(text):
    """Arapça sayıları doğru şekilde düzeltmek için fonksiyon"""
    arabic_numbers = {'1': '١', '2': '٢', '3': '٣', '4': '٤', '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩', '0': '٠'}
    corrected_text = ''
    for char in text:
        if char in arabic_numbers:
            corrected_text += arabic_numbers[char]
        else:
            corrected_text += char
    return corrected_text

def fetch_url_with_retries(url, retries=3, delay=2):
    """URL'yi hata durumunda yeniden denemelerle al."""
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                print(f"URL çekilemedi: {url}, Hata: {e}")
    return None

def extract_arabic_ayets(html_content):
    """HTML içeriğinden Arapça ayetleri ayıkla ve her birini tek satır yap."""
    soup = BeautifulSoup(html_content, 'html.parser')
    ayet_text = soup.find("div", class_="alert alert-info")
    if not ayet_text:
        return []
    
    raw_text = ayet_text.text.strip()
    # Satır sonlarını ve gereksiz boşlukları kaldır
    cleaned_text = re.sub(r'\s+', ' ', raw_text).strip()
    
    # Arapça ayetleri bölmek için `﴿` ve `﴾` karakterlerini kullan
    ayet_list = re.split(r'﴾\s*', cleaned_text)
    ayet_list = [ayet.strip() + "﴾" for ayet in ayet_list if ayet.strip()]
    return ayet_list

def get_ayet_data(ayet_url):
    """Belirli bir ayet URL'sinden Arapça ayetleri al."""
    response = fetch_url_with_retries(ayet_url)
    if not response:
        return []
    
    arabic_ayets = extract_arabic_ayets(response.content)
    # Sayıları düzeltmek için Arapça sayıları kontrol et ve düzelt
    arabic_ayets = [correct_arabic_numbers(ayet) for ayet in arabic_ayets]
    return {"ayet_url": ayet_url, "arabic_ayets": arabic_ayets}

def fetch_all_ayets(sure_id):
    """Bir surenin tüm ayetlerini almak için URL'leri döndüren fonksiyon"""
    url = f"https://kuran.diyanet.gov.tr/tefsir/sure/{sure_id}"
    response = fetch_url_with_retries(url)
    if not response:
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    ayet_links = []
    base_url = "https://kuran.diyanet.gov.tr"  # Tam URL'yi ekliyoruz
    for ayet in soup.find_all("a", href=True):
        if "/tefsir/" in ayet['href']:
            full_url = base_url + ayet['href']  # Tam URL'yi oluşturuyoruz
            ayet_links.append(full_url)
    
    return ayet_links


def process_ayet_links(ayet_links):
    """Ayet bağlantılarını işleyerek Arapça metinleri çek."""
    ayet_data_list = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        ayet_results = list(tqdm(executor.map(get_ayet_data, ayet_links), total=len(ayet_links), desc="Ayetler Çekiliyor"))
        for result in ayet_results:
            ayet_data_list.append(result)
    return ayet_data_list

def get_all_sure_ayetler():
    """Tüm surelerin ayetlerini çeker ve veriyi döndürür"""
    sure_ids = range(1, 115)  # Kuran'daki tüm sureler 1'den 114'e kadar
    all_ayet_data = []
    
    for sure_id in sure_ids:
        print(f"{sure_id}. Sure çekiliyor...")
        ayet_links = fetch_all_ayets(sure_id)
        ayet_data = process_ayet_links(ayet_links)
        all_ayet_data.extend(ayet_data)
    
    return all_ayet_data

# Tüm sureler için ayet verilerini çek
all_ayet_data = get_all_sure_ayetler()

# Verileri CSV'ye kaydet
ayet_df = pd.DataFrame(
    [
        {"ayet_url": ayet["ayet_url"], "arabic_ayet": ayet_text}
        for ayet in all_ayet_data
        for ayet_text in ayet["arabic_ayets"]
    ]
)
ayet_df.to_csv("tüm_sureler_arapca_ayetler6.csv", index=False, encoding="utf-8-sig")
