import os
import sys
import time
import requests
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

geolocator = Nominatim(user_agent="fullet_opet_bot")

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
        print(f" [!] {ilce} icin koordinat cekilirken zaman asimi oldu.")
    except Exception as e:
        print(f" [!] Geocode Hatasi ({ilce}): {str(e)}")
        
    return None, None

def scrape_opet_data():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Opet Botu Devrede! API taranıyor...")
    scraped_data = []
    
    # Opet'in il bazli (MERKEZ) baz fiyat donen listesi
    target_mappings = {
        "İSTANBUL ANADOLU": "Kadikoy",
        "ANKARA": "Cankaya",
        "İZMİR": "Konak",
        "İSTANBUL AVRUPA": "Beylikduzu"
    }
    
    try:
        response = requests.get("https://api.opet.com.tr/api/fuelprices/allprices", timeout=15)
        response.encoding = 'utf-8' # Turkce karakterleri dogru almak icin
        data = response.json()
        
        print("[+] Opet API'sinden veri basariyla cekildi. Hedef lokasyonlar ayiklaniyor...")
        
        for location_data in data:
            prov = location_data.get("provinceName", "")
            
            if prov in target_mappings:
                city = "ISTANBUL" if "İSTANBUL" in prov else prov.replace("İ", "I")
                district = target_mappings[prov]
                
                fiyatlar = {}
                for price_item in location_data.get("prices", []):
                    name = price_item.get("productName", "").lower()
                    amt = price_item.get("amount", 0)
                    if "kurşunsuz" in name or "benzin" in name:
                        fiyatlar["Kursunsuz 95"] = float(amt)
                    elif "motorin eco" in name or "motorin ult" in name:
                        fiyatlar["Motorin"] = float(amt)
                    elif "oto gaz" in name or "lpg" in name:
                        fiyatlar["LPG"] = float(amt)
                
                # Sadece Opet'in "X subesi" icin koordinat uretelim
                enlem, boylam = get_coordinates(city, district, "Opet")
                
                istasyon_adi = f"Opet {district.title()} (Fullet Verisi)"
                scraped_data.append({
                    "il": city,
                    "ilce": district.upper(),
                    "istasyon_adi": istasyon_adi,
                    "enlem": enlem,
                    "boylam": boylam,
                    "fiyatlar": fiyatlar
                })
                time.sleep(1) # Nominatim 1 sn bekleme payi
                
        return scraped_data
        
    except Exception as e:
        print(f"Scraping Hatasi: {str(e)}")
        return scraped_data

def save_to_supabase(data):
    if not supabase:
        print("\n[!] DIKKAT: Supabase anahtarlari eksik.")
        return
        
    print(f"\n[+] {len(data)} OPET istasyon verisi Supabase'e isleniyor...")
    
    for item in data:
        try:
            res = supabase.table("istasyonlar").select("id, enlem, boylam").eq("isim", item["istasyon_adi"]).execute()
            if len(res.data) == 0:
                ins = supabase.table("istasyonlar").insert({
                    "marka": "Opet", 
                    "isim": item["istasyon_adi"], 
                    "il": item["il"], 
                    "ilce": item["ilce"],
                    "enlem": item.get("enlem"),
                    "boylam": item.get("boylam")
                }).execute()
                istasyon_id = ins.data[0]["id"]
            else:
                istasyon_id = res.data[0]["id"]
                if item.get("enlem") and item.get("boylam") and (res.data[0].get("enlem") is None):
                    supabase.table("istasyonlar").update({
                        "enlem": item["enlem"],
                        "boylam": item["boylam"]
                    }).eq("id", istasyon_id).execute()
                
            for yakit_tipi, fiyat in item["fiyatlar"].items():
                supabase.table("fiyatlar").upsert({
                    "istasyon_id": istasyon_id, "yakit_tipi": yakit_tipi, "fiyat": fiyat
                }, on_conflict="istasyon_id, yakit_tipi").execute()
                
        except Exception as e:
            print(f"[!] Supabase DB Hatasi ({item['istasyon_adi']}): {str(e)}")
            
    print("[✓] OPET verileri basariyla Supabase'e yazildi!")

if __name__ == "__main__":
    print("=" * 60)
    print("      OPET GERCEK ZAMANLI VERI KAZIYICI (API-BASED)")
    print("=" * 60)
    
    start_time = datetime.now()
    veriler = scrape_opet_data()
    
    if veriler:
        print("\n--- ÇEKİLEN OPET VERİLERİ ---")
        for v in veriler:
            coord_str = f"[{v['enlem']}, {v['boylam']}]" if v.get('enlem') else "[Bulunamadi]"
            print(f" > {v['istasyon_adi']} {coord_str} | Benzin: {v['fiyatlar'].get('Kursunsuz 95', '-')} TL | Motorin: {v['fiyatlar'].get('Motorin', '-')} TL")
            
        save_to_supabase(veriler)
    else:
        print("[-] Herhangi bir veri cekilemedi!")
        
    print(f"\n[OK] Opet Gorevi Tamamlandi! Sure: {(datetime.now() - start_time).total_seconds():.1f} sn.")
