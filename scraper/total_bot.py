import sys
from datetime import datetime

from http_utils import HTTP

from db_utils import parse_price, save_regional_prices_to_supabase

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

API_BASE = "https://apimobile.guzelenerji.com.tr"
SOURCE = "apimobile.guzelenerji.com.tr/exapi/fuel_prices"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Fullet fuel price monitor)",
    "Origin": "https://akaryakitfiyatlari.totalenergiesistasyonlari.com.tr",
    "Referer": "https://akaryakitfiyatlari.totalenergiesistasyonlari.com.tr/",
}


def _get_json(path):
    response = HTTP.get(f"{API_BASE}{path}", headers=HEADERS, timeout=(5, 30))
    response.raise_for_status()
    return response.json()


def scrape_data():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] TotalEnergies bot started.")
    scraped_data = []

    try:
        cities = _get_json("/exapi/fuel_price_cities")
        active_cities = [city for city in cities if city.get("active") is True]

        for city in active_cities:
            city_id = city.get("city_id")
            city_name = city.get("city_name")
            if city_id is None or not city_name:
                continue

            rows = _get_json(f"/exapi/fuel_prices/{city_id}")
            for row in rows:
                district = row.get("county_name") or ""
                prices = {
                    "Kursunsuz 95": parse_price(row.get("kursunsuz_95_excellium_95")),
                    "Motorin": parse_price(row.get("motorin")),
                    "LPG": parse_price(row.get("otogaz")),
                }
                prices = {
                    fuel: price
                    for fuel, price in prices.items()
                    if price is not None
                }
                if not prices:
                    continue

                scraped_data.append({
                    "marka": "TotalEnergies",
                    "il": city_name,
                    "ilce": district,
                    "fiyatlar": prices,
                    "veri_kaynagi": SOURCE,
                })
    except Exception as exc:
        print(f"[WARN] TotalEnergies scrape failed: {exc}")

    return scraped_data


if __name__ == "__main__":
    start_time = datetime.now()
    data = scrape_data()
    save_regional_prices_to_supabase(data, default_brand="TotalEnergies")
    print(f"[OK] TotalEnergies finished in {(datetime.now() - start_time).total_seconds():.1f}s.")
