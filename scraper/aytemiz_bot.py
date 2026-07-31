import sys
from datetime import datetime

from bs4 import BeautifulSoup

from http_utils import HTTP
from db_utils import parse_price, save_to_supabase

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def _parse_table_rows(soup):
    table = soup.select_one("table")
    if table is None:
        return

    tokens = table.get_text("\n", strip=True).split("\n")
    price_start = 6
    index = price_start
    while index + 5 < len(tokens):
        city = tokens[index]
        if parse_price(tokens[index + 1]) is None:
            index += 1
            continue
        yield [
            city,
            tokens[index + 1],
            tokens[index + 2],
        ]
        index += 6


def scrape_data():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Aytemiz bot started.")
    scraped_data = []

    try:
        response = HTTP.get(
            "https://www.aytemiz.com.tr/akaryakit-fiyatlari/benzin-fiyatlari",
            headers={"User-Agent": "Mozilla/5.0 (Fullet fuel price monitor)"},
            timeout=(5, 20),
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for cols in _parse_table_rows(soup):
            city = cols[0]
            prices = {
                "Kursunsuz 95": parse_price(cols[1]),
                "Motorin": parse_price(cols[2]),
            }
            prices = {fuel: price for fuel, price in prices.items() if price is not None}
            if not prices:
                continue

            scraped_data.append({
                "marka": "Aytemiz",
                "il": city,
                "ilce": "",
                "fiyatlar": prices,
                "veri_kaynagi": "aytemiz.com.tr/akaryakit-fiyatlari",
            })
    except Exception as exc:
        print(f"[WARN] Aytemiz scrape failed: {exc}")

    return scraped_data


if __name__ == "__main__":
    start_time = datetime.now()
    data = scrape_data()
    save_to_supabase(data, default_brand="Aytemiz")
    print(f"[OK] Aytemiz finished in {(datetime.now() - start_time).total_seconds():.1f}s.")
