import requests
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm
import re
from concurrent.futures import ThreadPoolExecutor
import time

BASE_URL = "https://kuran.diyanet.gov.tr"

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
    """HTML içeriğinden Arapça ayetleri ayıkla ve her birini ayrı listeye koy."""
    soup = BeautifulSoup(html_content, 'html.parser')
    ayet_text = soup.find("div", class_="alert alert-info")
    if not ayet_text:
        return []
    
    raw_text = ayet_text.text.strip()
    # Arapça ayetleri bölmek için `﴿` ve `﴾` karakterlerini kullan
    ayet_list = re.split(r'﴾\s*', raw_text)
    ayet_list = [ayet.strip() + "﴾" for ayet in ayet_list if ayet.strip()]
    return ayet_list

def get_ayet_data(ayet_url):
    """Belirli bir ayet URL'sinden Arapça ayetleri al."""
    response = fetch_url_with_retries(ayet_url)
    if not response:
        return []
    
    arabic_ayets = extract_arabic_ayets(response.content)
    return {"ayet_url": ayet_url, "arabic_ayets": arabic_ayets}

def process_ayet_links(ayet_links):
    """Ayet bağlantılarını işleyerek Arapça metinleri çek."""
    ayet_data_list = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        ayet_results = list(tqdm(executor.map(get_ayet_data, ayet_links), total=len(ayet_links), desc="Ayetler Çekiliyor"))
        for result in ayet_results:
            ayet_data_list.append(result)
    return ayet_data_list

def fetch_all_ayets(sure_id):
    """Bir surenin tüm ayet bağlantılarını çek."""
    sure_url = f"{BASE_URL}/tefsir/sure/{sure_id}"
    response = fetch_url_with_retries(sure_url)
    if not response:
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    ayet_links = soup.find("div", class_="panel-body").find_all("a", href=True)
    return [BASE_URL + link['href'] for link in ayet_links]

# Örnek: Sadece Bakara Suresinin ayetleri için
ayet_links = fetch_all_ayets(2)  # Bakara suresi ID'si 2
ayet_data = process_ayet_links(ayet_links)

# Verileri CSV'ye kaydet
ayet_df = pd.DataFrame(
    [
        {"ayet_url": ayet["ayet_url"], "arabic_ayet": ayet_text}
        for ayet in ayet_data
        for ayet_text in ayet["arabic_ayets"]
    ]
)
ayet_df.to_csv("arapca_ayetler_duzgun4.csv", index=False, encoding="utf-8-sig")
