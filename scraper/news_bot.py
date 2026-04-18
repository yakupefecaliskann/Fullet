import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

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

def scrape_fuel_news():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sondakika Haber Botu Devrede! Google News taranıyor...")
    
    # Haberleri dondur
    scraped_news = []
    
    # Benzin ve motorin zammı veya indirimi olan güncel haberlerin RSS bağlantısı
    rss_url = "https://news.google.com/rss/search?q=akaryak%C4%B1t+zamm%C4%B1+OR+benzin+indirimi+OR+motorin&hl=tr&gl=TR&ceid=TR:tr"
    
    try:
        response = requests.get(rss_url, timeout=10)
        root = ET.fromstring(response.content)
        
        channel = root.find("channel")
        items = channel.findall("item")
        
        print(f"[+] {len(items)} adet haber bulundu. Ayıklanıyor...")
        
        for item in items[:10]: # En guncel 10 haberi al
            title = item.find("title").text
            link = item.find("link").text
            pubDate = item.find("pubDate").text
            source = item.find("source").text if item.find("source") is not None else "Haber"
            
            # Formati sadelestir: "Haber Basligi - Kaynak Adi" seklinde gelen title'dan kaynagi cikar
            clean_title = title.split(" - ")[0]
            
            scraped_news.append({
                "baslik": clean_title,
                "link": link,
                "kaynak": source,
                "tarih": pubDate
            })
            
        return scraped_news
    except Exception as e:
        print(f"Haber Cekme Hatasi: {e}")
        return []

def save_to_supabase(news_list):
    if not supabase:
        print("\n[!] Supabase baglantisi yok.")
        return
        
    print(f"\n[+] {len(news_list)} Haber Supabase'e yazilmaya calisiliyor...")
    try:
        # Table exist check? Supabase REST doesn't allow direct DDL. We just try to insert.
        for news in news_list:
            # Sadece ayni linke sahip haber yoksa insert et (on_conflict icin PK/Unique gerekebilir, biz basit bir kontrol yapalim)
            res = supabase.table("haberler").select("id").eq("link", news["link"]).execute()
            if len(res.data) == 0:
                supabase.table("haberler").insert({
                    "baslik": news["baslik"],
                    "link": news["link"],
                    "kaynak": news["kaynak"]
                }).execute()
        print("[✓] Sondakika Haberleri başarıyla veritabanına eklendi!")
        
    except Exception as e:
        error_msg = str(e)
        if "relation \"public.haberler\" does not exist" in error_msg:
            print("\n[HATA] 'haberler' tablosu Supabase'de bulunamadi!")
            print("Lutfen once 'database/create_haberler.sql' dosyasindaki kodu Supabase SQL Editor'e yapistirip calistirin.")
        else:
            print(f"\n[!] Supabase DB Hatasi: {error_msg}")

if __name__ == "__main__":
    print("=" * 60)
    print("      FULLET FOMO HABER KAZIYICI (Google News RSS)")
    print("=" * 60)
    
    haberler = scrape_fuel_news()
    
    if haberler:
        print("\n--- ÇEKİLEN HABERLER ---")
        for h in haberler:
            print(f" 📰 [{h['kaynak']}] {h['baslik']}")
            
        save_to_supabase(haberler)
    else:
        print("[-] Haber bulunamadi veya cekilemedi.")
