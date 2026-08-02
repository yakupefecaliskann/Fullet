import sys
from datetime import datetime

from http_utils import HTTP

from db_utils import finish_bot_run, save_station_inventory_to_supabase

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

API_BASE = "https://apimobile.guzelenerji.com.tr"
SOURCE = "apimobile.guzelenerji.com.tr/exapi/stations"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Fullet official station inventory)",
    "Origin": "https://akaryakitfiyatlari.totalenergiesistasyonlari.com.tr",
    "Referer": "https://akaryakitfiyatlari.totalenergiesistasyonlari.com.tr/",
}


def _get_json(path):
    response = HTTP.get(f"{API_BASE}{path}", headers=HEADERS, timeout=(5, 30))
    response.raise_for_status()
    return response.json()


def _station_name(row):
    canopy_code = str(row.get("canopy_code") or "").strip()
    station_code = str(row.get("station_code") or "").strip()
    if canopy_code and station_code:
        return f"{canopy_code} ({station_code})"
    return canopy_code or str(row.get("name") or "").strip()


def scrape_data():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] TotalEnergies station bot started.")
    scraped_data = []

    try:
        rows = _get_json("/exapi/stations")
        for row in rows:
            raw_brand = str(row.get("brand") or "")
            if "total" not in raw_brand.lower():
                continue
            if row.get("is_active") is False:
                continue

            scraped_data.append({
                "marka": "TotalEnergies",
                "istasyon_adi": _station_name(row),
                "resmi_unvan": row.get("name"),
                "il": row.get("city"),
                "ilce": row.get("county"),
                "adres": row.get("address"),
                "enlem": row.get("latitude"),
                "boylam": row.get("longitude"),
                "veri_kaynagi": SOURCE,
            })
    except Exception as exc:
        print(f"[WARN] TotalEnergies station scrape failed: {exc}")

    return scraped_data


if __name__ == "__main__":
    start_time = datetime.now()
    data = scrape_data()
    print(f"[INFO] TotalEnergies official station rows fetched: {len(data)}")
    summary = save_station_inventory_to_supabase(data, default_brand="TotalEnergies")
    print(f"[OK] TotalEnergies station bot finished in {(datetime.now() - start_time).total_seconds():.1f}s.")
    raise SystemExit(finish_bot_run("total_station_bot.py", scraped=len(data), summary=summary))
