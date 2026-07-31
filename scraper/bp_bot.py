import sys
import re
from datetime import datetime

from bs4 import BeautifulSoup

from http_utils import HTTP
from db_utils import parse_price, save_to_supabase

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def _first_price(cell_text):
    match = re.search(r"\d{1,3}[.,]\d{2}", cell_text or "")
    return parse_price(match.group(0)) if match else None


def scrape_data():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] BP bot started.")
    scraped_data = []

    try:
        response = HTTP.get(
            "https://www.petrolofisi.com.tr/akaryakit-fiyatlari-bp",
            headers={"User-Agent": "Mozilla/5.0 (Fullet fuel price monitor)"},
            timeout=(5, 20),
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        rows = soup.select("table tr")
        for row in rows:
            cols = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
            if len(cols) < 3:
                continue
            if cols[0].lower() in ("şehir", "sehir"):
                continue

            city = cols[0]
            prices = {
                "Kursunsuz 95": _first_price(cols[1]),
                "Motorin": _first_price(cols[3] if len(cols) > 3 else cols[2]),
            }
            if len(cols) > 8:
                prices["LPG"] = _first_price(cols[8])
            prices = {fuel: price for fuel, price in prices.items() if price is not None}
            if not prices:
                continue

            scraped_data.append({
                "marka": "BP",
                "il": city,
                "ilce": "",
                "fiyatlar": prices,
                "veri_kaynagi": "petrolofisi.com.tr/akaryakit-fiyatlari-bp",
            })
    except Exception as exc:
        print(f"[WARN] BP scrape failed: {exc}")

    return scraped_data


if __name__ == "__main__":
    start_time = datetime.now()
    data = scrape_data()
    save_to_supabase(data, default_brand="BP")
    print(f"[OK] BP finished in {(datetime.now() - start_time).total_seconds():.1f}s.")
