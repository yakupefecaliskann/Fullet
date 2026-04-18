import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from playwright.sync_api import sync_playwright
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

# Nominatim API (Ucretsiz) kullanarak koordinat bulma
geolocator = Nominatim(user_agent="fullet_scraper_bot")

def get_coordinates(il, ilce, marka):
    try:
        # 1. Taktik: Daha spesifik arama (Adresteki tum parcalari ver)
        query = f"{marka}, {ilce}, {il}, Türkiye"
        location = geolocator.geocode(query, timeout=5)
        if location:
            return location.latitude, location.longitude
        
        # 2. Taktik: Bulamazsa sadece İlce ve İl adina gore merkez koordinatini al
        query_fallback = f"{ilce}, {il}, Türkiye"
        location = geolocator.geocode(query_fallback, timeout=5)
        if location:
            return location.latitude, location.longitude
            
    except GeocoderTimedOut:
        print(f" [!] {ilce} icin koordinat cekilirken zaman asimi oldu.")
    except Exception as e:
        print(f" [!] Geocode Hatasi ({ilce}): {str(e)}")
        
    return None, None

def scrape_shell_data(target_locations=[{"il": "ISTANBUL", "ilce": "KADIKOY"}, {"il": "ANKARA", "ilce": "CANKAYA"}, {"il": "IZMIR", "ilce": "KONAK"}]):
    """Shell'in sayfasinda Il ve Ilce secer, AJAX bekler, fiyatlari okur."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Kasklar takildi, Tarayici (Playwright) piste cikiyor...")
    scraped_data = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto("https://www.turkiyeshell.com/pompatest/History.aspx", timeout=60000)
            print("[+] Shell Fiyat Paneline basariyla sizildi. Kazima basliyor...")
            
            for loc in target_locations:
                city = loc["il"]
                county = loc["ilce"]
                print(f"\n[>] Hedef Lokasyon: {city} - {county}")
                
                # 1. IL Sec ve Yuklenmesini Bekle
                page.locator("#cb_all_cb_province_B-1Img").click()
                page.wait_for_timeout(1000)
                city_locator = page.locator(f"#cb_all_cb_province_DDD_L_LBT td:has-text('{city}')").first
                if city_locator.is_visible():
                    city_locator.click()
                    page.wait_for_timeout(2500) # AJAX
                else:
                    page.keyboard.press("Escape")
                
                # 2. ILCE Sec ve Yuklenmesini Bekle
                page.locator("#cb_all_cb_county_B-1Img").click()
                page.wait_for_timeout(1000)
                county_locator = page.locator(f"#cb_all_cb_county_DDD_L_LBT td:has-text('{county}')").first
                if county_locator.is_visible():
                    county_locator.click()
                    page.wait_for_timeout(2500) # AJAX
                else:
                    page.keyboard.press("Escape")
                
                # 3. Butona Tikla
                page.locator("#cb_all_ASPxButton1_CD").click()
                page.wait_for_timeout(4000)
                
                # 4. Tablodaki Fiyatlari Topla
                rows = page.locator("#cb_all_grdPrices_DXMainTable tr.dxgvDataRow").all()
                print(f"   => {len(rows)} benzinlik verisi bulundu. Fiyatlar cekiliyor...")
                
                for row in rows:
                    cols = row.locator("td").all_inner_texts()
                    if len(cols) < 13: continue 
                    
                    ilce_isim = cols[2].strip()
                    fs_benzin = cols[3].strip().replace(",", ".")
                    fs_motorin = cols[5].strip().replace(",", ".")
                    lpg = cols[12].strip().replace(",", ".")
                    
                    fiyatlar = {}
                    if fs_benzin != "-": fiyatlar["Kursunsuz 95"] = float(fs_benzin)
                    if fs_motorin != "-": fiyatlar["Motorin"] = float(fs_motorin)
                    if lpg != "-": fiyatlar["LPG"] = float(lpg)
                    
                    # KOORDINATLAR CEKILIYOR
                    enlem, boylam = get_coordinates(city, ilce_isim, "Shell")
                    
                    scraped_data.append({
                        "il": city,
                        "ilce": ilce_isim,
                        "istasyon_adi": f"Shell {ilce_isim.capitalize()} (Fullet Verisi)",
                        "enlem": enlem,
                        "boylam": boylam,
                        "fiyatlar": fiyatlar
                    })
                    
            return scraped_data
            
        except Exception as e:
            print(f"Scraping Hatasi: {str(e)}")
            return scraped_data
        finally:
            browser.close()

def save_to_supabase(data):
    if not supabase:
        print("\n[!] DIKKAT: .env dosyasina Supabase anahtarlari girilmedigi icin veri buluta gonderilemedi.")
        return
        
    print(f"\n[+] Supabase baglantisi basarili. {len(data)} istasyon veritabanina gonderiliyor...")
    
    for item in data:
        try:
            res = supabase.table("istasyonlar").select("id, enlem, boylam").eq("isim", item["istasyon_adi"]).execute()
            if len(res.data) == 0:
                ins = supabase.table("istasyonlar").insert({
                    "marka": "Shell", 
                    "isim": item["istasyon_adi"], 
                    "il": item["il"], 
                    "ilce": item["ilce"],
                    "enlem": item.get("enlem"),
                    "boylam": item.get("boylam")
                }).execute()
                istasyon_id = ins.data[0]["id"]
            else:
                istasyon_id = res.data[0]["id"]
                # Mevcut istasyonun eger koordinatlari bombossa guncelle!
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
            
    print("[✓] MUHTESEM! Tum veriler Supabase'e islendi.")

if __name__ == "__main__":
    print("=" * 60)
    print("[FULLET] - GERCEK ZAMANLI VERI KAZIYICI V3.0 (SUPER BOT)")
    print("=" * 60)
    
    start_time = datetime.now()
    
    veriler = scrape_shell_data([
        {"il": "ISTANBUL", "ilce": "KADIKOY"}, 
        {"il": "ANKARA", "ilce": "CANKAYA"}, 
        {"il": "IZMIR", "ilce": "KONAK"}
    ])
    
    if veriler:
        print("\n--- CEKILEN ALTIN DEGERINDEKI GERCEK VERILER (KOORDINATLI) ---")
        for v in veriler:
            coord_str = f"[{v['enlem']}, {v['boylam']}]" if v.get('enlem') else "[Bulunamadi]"
            print(f" > {v['istasyon_adi']} {coord_str} | Benzin: {v['fiyatlar'].get('Kursunsuz 95', '-')} TL | Motorin: {v['fiyatlar'].get('Motorin', '-')} TL")
            
        save_to_supabase(veriler)
    
    print(f"\n[OK] Kusursuz operasyon! Toplam Sure: {(datetime.now() - start_time).total_seconds():.1f} saniye.")
