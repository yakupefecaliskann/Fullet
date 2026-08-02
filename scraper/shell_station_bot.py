import html
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urljoin
import json

import requests

from db_utils import finish_bot_run, normalize_city, save_station_inventory_to_supabase

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

BASE_URL = "https://find.shell.com"
LOCATIONS_URL = f"{BASE_URL}/tr/fuel/locations/tr_TR"
SOURCE = "find.shell.com/tr/fuel"
HEADERS = {"User-Agent": "Mozilla/5.0 (Fullet official station inventory)"}
MAX_WORKERS = 12

PROVINCES = {
    "ADANA", "ADIYAMAN", "AFYONKARAHISAR", "AGRI", "AKSARAY", "AMASYA",
    "ANKARA", "ANTALYA", "ARDAHAN", "ARTVIN", "AYDIN", "BALIKESIR",
    "BARTIN", "BATMAN", "BAYBURT", "BILECIK", "BINGOL", "BITLIS",
    "BOLU", "BURDUR", "BURSA", "CANAKKALE", "CANKIRI", "CORUM",
    "DENIZLI", "DIYARBAKIR", "DUZCE", "EDIRNE", "ELAZIG", "ERZINCAN",
    "ERZURUM", "ESKISEHIR", "GAZIANTEP", "GIRESUN", "GUMUSHANE",
    "HAKKARI", "HATAY", "IGDIR", "ISPARTA", "ISTANBUL", "IZMIR",
    "KAHRAMANMARAS", "KARABUK", "KARAMAN", "KARS", "KASTAMONU",
    "KAYSERI", "KILIS", "KIRIKKALE", "KIRKLARELI", "KIRSEHIR",
    "KOCAELI", "KONYA", "KUTAHYA", "MALATYA", "MANISA", "MARDIN",
    "MERSIN", "MUGLA", "MUS", "NEVSEHIR", "NIGDE", "ORDU", "OSMANIYE",
    "RIZE", "SAKARYA", "SAMSUN", "SANLIURFA", "SIIRT", "SINOP",
    "SIRNAK", "SIVAS", "TEKIRDAG", "TOKAT", "TRABZON", "TUNCELI",
    "USAK", "VAN", "YALOVA", "YOZGAT", "ZONGULDAK",
}


def _react_props(text):
    match = re.search(r'data-react-props="([^"]+)"', text)
    if not match:
        return {}
    return json.loads(html.unescape(match.group(1)))


def _get(url):
    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as exc:
            last_error = exc
            time.sleep(1 + attempt)
    raise last_error


def _locations_index():
    props = _react_props(_get(LOCATIONS_URL))
    locations = props.get("geographicListProps", {}).get("locations") or []
    return [
        {
            "name": item.get("name") or "",
            "url": urljoin(BASE_URL, item.get("link") or ""),
            "count": item.get("count") or 0,
        }
        for item in locations
        if item.get("link")
    ]


def _station_links(location_page):
    props = _react_props(_get(location_page["url"]))
    stations = props.get("stationListProps", {}).get("locations") or []
    parsed = []
    for station in stations:
        link = station.get("link")
        if not link:
            continue
        parsed.append({
            "group_name": location_page["name"],
            "url": urljoin(BASE_URL, link),
            "list_name": station.get("name"),
            "list_address": station.get("formatted_address"),
        })
    return parsed


def _city_district_from_text(value):
    candidates = [part for part in re.split(r"[\n,]+", value or "") if part.strip()]
    candidates.append(value or "")
    for candidate in reversed(candidates):
        normalized = normalize_city(candidate)
        if not normalized or normalized == "TR":
            continue
        normalized = re.sub(r"\b\d{4,6}\b", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip(" -/")
        for province in sorted(PROVINCES, key=len, reverse=True):
            match = re.search(rf"(^|[\s\-/]){re.escape(province)}($|[\s\-/])", normalized)
            if not match:
                continue
            before = normalized[:match.start()].strip(" -/")
            if before:
                before = re.sub(r"[^A-Z0-9 ]+", " ", before)
                before = re.sub(r"\s+", " ", before).strip()
            return province, before
    return "", ""


def _parse_station_detail(station):
    props = _react_props(_get(station["url"]))
    location = props.get("location") or {}
    address = location.get("formatted_address") or station.get("list_address") or ""
    city, district = _city_district_from_text(address)
    if not city:
        city, district = _city_district_from_text(station.get("group_name") or "")

    location_id_match = re.search(r"/fuel/(\d+)-", station["url"])
    location_id = location.get("location_id") or (
        location_id_match.group(1) if location_id_match else ""
    )
    name = location.get("name") or station.get("list_name")
    return {
        "marka": "Shell",
        "istasyon_adi": name,
        "resmi_unvan": f"{name} {location_id}" if name and location_id else name,
        "il": city,
        "ilce": district,
        "adres": address,
        "enlem": location.get("lat"),
        "boylam": location.get("lng"),
        "veri_kaynagi": SOURCE,
    }


def scrape_data():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Shell station bot started.")
    stations_by_url = {}

    try:
        location_pages = _locations_index()
        expected = sum(int(page["count"] or 0) for page in location_pages)
        print(f"[INFO] Shell location pages: {len(location_pages)}, listed station count: {expected}")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(_station_links, page) for page in location_pages]
            for future in as_completed(futures):
                try:
                    for station in future.result():
                        stations_by_url[station["url"]] = station
                except Exception as exc:
                    print(f"[WARN] Shell location page skipped: {exc}")

        print(f"[INFO] Shell station detail links: {len(stations_by_url)}")
        scraped_data = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [
                executor.submit(_parse_station_detail, station)
                for station in stations_by_url.values()
            ]
            for index, future in enumerate(as_completed(futures), start=1):
                try:
                    scraped_data.append(future.result())
                except Exception as exc:
                    print(f"[WARN] Shell station detail skipped: {exc}")
                if index % 100 == 0:
                    print(f"[INFO] Shell details parsed: {index}/{len(futures)}")

        return scraped_data
    except Exception as exc:
        print(f"[WARN] Shell station scrape failed: {exc}")
        return []


if __name__ == "__main__":
    start_time = datetime.now()
    data = scrape_data()
    print(f"[INFO] Shell official station rows fetched: {len(data)}")
    summary = save_station_inventory_to_supabase(data, default_brand="Shell")
    print(f"[OK] Shell station bot finished in {(datetime.now() - start_time).total_seconds():.1f}s.")
    raise SystemExit(finish_bot_run("shell_station_bot.py", scraped=len(data), summary=summary))
