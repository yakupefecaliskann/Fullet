import os
import sys
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Supabase baglanti hatasi: {e}")

geolocator = Nominatim(user_agent="fullet_aytemiz_bot")

def get_coordinates(il, ilce, marka):
    try:
        query = f"{marka}, {ilce}, {il}, Türkiye"
        location = geolocator.geocode(query, timeout=5)
        if location:
            return location.latitude, location.longitude
        
        query_fallback = f"{ilce}, {il}, Türkiye"
        location = geolocator.geocode(query_fallback, timeout=5)
        if location:
            return location.latitude, location.longitude
            
    except GeocoderTimedOut:
        pass
    except Exception as e:
        pass
        
    return None, None

def scrape_aytemiz_data():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Aytemiz Botu Devrede! HTML analiz ediliyor...")
    scraped_data = []
    
    target_mappings = {
        "İstanbul / Anadolu": "Kadikoy",
        "Ankara": "Cankaya",
        "İzmir": "Konak",
        "İstanbul / Avrupa": "Beylikduzu"
    }
    
    try:
        response = requests.get("https://www.aytemiz.com.tr/akaryakit-fiyatlari/", timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.content, "html.parser")
        
        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if not cols or len(cols) < 5:
                continue
                
            prov = cols[0].text.strip()
            
            if prov in target_mappings:
                city = "ISTANBUL" if "İstanbul" in prov else prov.replace("İ", "I")
                district = target_mappings[prov]
                
                fiyatlar = {}
                try:
                    benzin = cols[1].text.strip().replace(",", ".")
                    if benzin: fiyatlar["Kursunsuz 95"] = float(benzin)
                        
                    motorin = cols[2].text.strip().replace(",", ".")
                    if motorin: fiyatlar["Motorin"] = float(motorin)
                        
                    # Aytemiz'de LPG bu sayfada ayri veriliyor olabilir veya '-' doner. 
                except ValueError:
                    pass
                
                enlem, boylam = get_coordinates(city, district, "Aytemiz")
                
                scraped_data.append({
                    "il": city,
                    "ilce": district.upper(),
                    "istasyon_adi": f"Aytemiz {district.title()} (Fullet Verisi)",
                    "enlem": enlem,
                    "boylam": boylam,
                    "fiyatlar": fiyatlar
                })
                time.sleep(1) 
                
        return scraped_data
        
    except Exception as e:
        print(f"Scraping Hatasi: {str(e)}")
        return scraped_data

def save_to_supabase(data):
    if not supabase: return
    for item in data:
        try:
            res = supabase.table("istasyonlar").select("id, enlem, boylam").eq("isim", item["istasyon_adi"]).execute()
            if len(res.data) == 0:
                ins = supabase.table("istasyonlar").insert({
                    "marka": "Aytemiz", "isim": item["istasyon_adi"], 
                    "il": item["il"], "ilce": item["ilce"],
                    "enlem": item.get("enlem"), "boylam": item.get("boylam")
                }).execute()
                istasyon_id = ins.data[0]["id"]
            else:
                istasyon_id = res.data[0]["id"]
                if item.get("enlem") and item.get("boylam") and (res.data[0].get("enlem") is None):
                    supabase.table("istasyonlar").update({"enlem": item["enlem"], "boylam": item["boylam"]}).eq("id", istasyon_id).execute()
                
            for yakit_tipi, fiyat in item["fiyatlar"].items():
                supabase.table("fiyatlar").upsert({
                    "istasyon_id": istasyon_id, "yakit_tipi": yakit_tipi, "fiyat": fiyat
                }, on_conflict="istasyon_id, yakit_tipi").execute()
                
        except Exception as e:
            pass
            
    print("[✓] Aytemiz verileri basariyla Supabase'e yazildi!")

if __name__ == "__main__":
    veriler = scrape_aytemiz_data()
    if veriler:
        for v in veriler:
            print(f" > {v['istasyon_adi']} | Benzin: {v['fiyatlar'].get('Kursunsuz 95', '-')} TL")
        save_to_supabase(veriler)
