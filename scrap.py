import requests
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm

BASE_URL = "https://kuran.diyanet.gov.tr"
SURE_URL_TEMPLATE = "https://kuran.diyanet.gov.tr/tefsir/sure/{}"

def get_sure_data(sure_id):
    """Bir sureye ait bilgileri çek."""
    url = SURE_URL_TEMPLATE.format(sure_id)
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    sure_data = {}
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

def get_ayet_data(ayet_url):
    """Bir ayete ait bilgileri çek."""
    response = requests.get(ayet_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    ayet_data = {}
    try:
        ayet_data['ayet'] = soup.find("div", class_="alert alert-info").text.strip()
        ayet_data['meal'] = soup.find("div", class_="alert alert-warning").text.strip()
        ayet_data['tefsir'] = soup.find("div", class_="alert alert-success").text.strip()
    except AttributeError:
        pass
    
    return ayet_data

# Sure ve Ayet Verilerini Topla
sure_list = []  # Sure bilgileri için
ayet_list = []  # Ayet bilgileri için

for sure_id in tqdm(range(1, 115)):  # 1'den 114'e kadar sure ID'leri
    sure_data = get_sure_data(sure_id)
    sure_list.append(sure_data)
    
    for ayet_url in sure_data.get('ayet_links', []):
        ayet_data = get_ayet_data(ayet_url)
        ayet_data['sure_id'] = sure_id
        ayet_list.append(ayet_data)

# Verileri CSV'ye Kaydet
sure_df = pd.DataFrame(sure_list)
ayet_df = pd.DataFrame(ayet_list)

sure_df.to_csv("sureler.csv", index=False, encoding='utf-8-sig')
ayet_df.to_csv("ayetler.csv", index=False, encoding='utf-8-sig')
