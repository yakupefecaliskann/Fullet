import sys
from datetime import datetime

import requests

from db_utils import save_station_inventory_to_supabase

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

BASE_URL = "https://www.tppd.com.tr"
SOURCE = "www.tppd.com.tr/tr/stationmaplist"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Fullet official station inventory)",
    "Referer": "https://www.tppd.com.tr/istasyonlar",
}


def scrape_data():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Turkiye Petrolleri station bot started.")
    scraped_data = []

    try:
        response = requests.get(
            f"{BASE_URL}/tr/stationmaplist",
            params={"cityID": 0},
            headers=HEADERS,
            timeout=30,
        )
        response.raise_for_status()
        rows = response.json()

        for row in rows:
            scraped_data.append({
                "marka": "Türkiye Petrolleri",
                "istasyon_adi": row.get("StationName"),
                "il": row.get("CityName"),
                "ilce": row.get("County"),
                "adres": row.get("Address"),
                "enlem": row.get("Lat"),
                "boylam": row.get("Lng"),
                "veri_kaynagi": SOURCE,
            })
    except Exception as exc:
        print(f"[WARN] Turkiye Petrolleri station scrape failed: {exc}")

    return scraped_data


if __name__ == "__main__":
    start_time = datetime.now()
    data = scrape_data()
    print(f"[INFO] Turkiye Petrolleri official station rows fetched: {len(data)}")
    save_station_inventory_to_supabase(data, default_brand="Türkiye Petrolleri")
    print(f"[OK] Turkiye Petrolleri station bot finished in {(datetime.now() - start_time).total_seconds():.1f}s.")
