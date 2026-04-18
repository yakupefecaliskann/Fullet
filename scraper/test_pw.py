from playwright.sync_api import sync_playwright
import time

def test_scraper():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.turkiyeshell.com/pompatest/History.aspx", timeout=60000)
        
        print("Il dropdown aciliyor...")
        page.locator("#cb_all_cb_province_B-1").click()
        page.wait_for_timeout(1000)
        
        print("ISTANBUL seciliyor...")
        page.locator("#cb_all_cb_province_DDD_L_LBT td:has-text('ISTANBUL')").first.click()
        
        # Ilce dropdown'un yuklenmesini bekle (Callback bitis)
        print("Il secimi sonrasi callback bekleniyor...")
        page.wait_for_timeout(3000)
        
        print("Fiyatlari Goster butonuna tiklaniyor...")
        page.locator("#cb_all_ASPxButton1").click()
        
        print("Tablonun yuklenmesi bekleniyor...")
        page.wait_for_timeout(5000)
        
        # debug HTML
        html = page.content()
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        rows = page.locator(".dxgvDataRow").all()
        print(f"Toplam {len(rows)} satir bulundu.")
        
        browser.close()

if __name__ == "__main__":
    test_scraper()
