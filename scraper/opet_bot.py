import sys
from datetime import datetime

from http_utils import HTTP

from db_utils import finish_bot_run, parse_price, save_to_supabase

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def scrape_opet_data():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Opet bot started.")
    scraped_data = []

    try:
        response = HTTP.get(
            "https://api.opet.com.tr/api/fuelprices/allprices",
            headers={"User-Agent": "Mozilla/5.0 (Fullet fuel price monitor)"},
            timeout=(5, 20),
        )
        response.raise_for_status()
        data = response.json()

        for location_data in data:
            city = location_data.get("provinceName", "")
            if not city:
                continue

            prices = {}
            for price_item in location_data.get("prices", []):
                name = str(price_item.get("productName", ""))
                price = parse_price(price_item.get("amount"))
                lower = name.lower()
                if price is None:
                    continue
                if "kurşunsuz" in lower or "benzin" in lower:
                    prices["Kursunsuz 95"] = price
                elif "motorin" in lower or "dizel" in lower:
                    prices["Motorin"] = price
                elif "oto gaz" in lower or "otogaz" in lower or "lpg" in lower:
                    prices["LPG"] = price

            if not prices:
                continue

            scraped_data.append({
                "marka": "Opet",
                "il": city,
                "ilce": "",
                "fiyatlar": prices,
                "veri_kaynagi": "api.opet.com.tr/api/fuelprices/allprices",
            })
    except Exception as exc:
        print(f"[WARN] Opet scrape failed: {exc}")

    return scraped_data


if __name__ == "__main__":
    start_time = datetime.now()
    data = scrape_opet_data()
    summary = save_to_supabase(data, default_brand="Opet")
    print(f"[OK] Opet finished in {(datetime.now() - start_time).total_seconds():.1f}s.")
    raise SystemExit(finish_bot_run("opet_bot.py", scraped=len(data), summary=summary))
