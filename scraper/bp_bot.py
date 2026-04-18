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
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

geolocator = Nominatim(user_agent="fullet_bp_bot")

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
    except:
        pass
    return None, None

def scrape_bp_data():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] BP Botu Devrede!")
    print("[INFO] BP Turkiye organizasyonu Petrol Ofisi satin aldigi icin fiyatlar birebir PO tabanlidir. PO altyapisindan BP isimli mirror olusturuluyor...")
    scraped_data = []
    
    target_mappings = {"ISTANBUL (ANADOLU)": "Kadikoy", "ANKARA": "Cankaya", "IZMIR": "Konak", "ISTANBUL (AVRUPA)": "Beylikduzu"}
    
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get("https://www.petrolofisi.com.tr/akaryakit-fiyatlari", headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, "html.parser")
        
        rows = soup.select("table tbody tr")
        for row in rows:
            cols = row.find_all("td")
            if not cols or len(cols) < 7: continue
                
            prov = cols[0].text.strip()
            
            if prov in target_mappings:
                city = "ISTANBUL" if "ISTANBUL" in prov else prov
                district = target_mappings[prov]
                fiyatlar = {}
                try:
                    benzin = cols[1].text.strip().split('\n')[0].replace(",", ".")
                    if benzin and benzin != "-": fiyatlar["Kursunsuz 95"] = float(benzin)
                        
                    motorin = cols[2].text.strip().split('\n')[0].replace(",", ".")
                    if motorin and motorin != "-": fiyatlar["Motorin"] = float(motorin)
                        
                    lpg = cols[6].text.strip().split('\n')[0].replace(",", ".")
                    if lpg and lpg != "-": fiyatlar["LPG"] = float(lpg)
                except ValueError:
                    pass
                
                enlem, boylam = get_coordinates(city, district, "BP")
                
                istasyon_adi = f"BP {district.title()} (Fullet Verisi)"
                scraped_data.append({
                    "il": city, "ilce": district.upper(), "istasyon_adi": istasyon_adi,
                    "enlem": enlem, "boylam": boylam, "fiyatlar": fiyatlar
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
                    "marka": "BP", "isim": item["istasyon_adi"], 
                    "il": item["il"], "ilce": item["ilce"],
                    "enlem": item.get("enlem"), "boylam": item.get("boylam")
                }).execute()
                istasyon_id = ins.data[0]["id"]
            else:
                istasyon_id = res.data[0]["id"]
                if item.get("enlem") and item.get("boylam") and (res.data[0].get("enlem") is None):
                    supabase.table("istasyonlar").update({"enlem": item["enlem"], "boylam": item["boylam"]}).eq("id", istasyon_id).execute()
                
            for yakit_tipi, fiyat in item["fiyatlar"].items():
                supabase.table("fiyatlar").upsert({"istasyon_id": istasyon_id, "yakit_tipi": yakit_tipi, "fiyat": fiyat}, on_conflict="istasyon_id, yakit_tipi").execute()
        except: pass
    print("[✓] BP verileri basariyla Supabase'e yazildi!")

if __name__ == "__main__":
    veriler = scrape_bp_data()
    if veriler:
        for v in veriler: print(f" > {v['istasyon_adi']} | Benzin: {v['fiyatlar'].get('Kursunsuz 95', '-')} TL")
        save_to_supabase(veriler)
