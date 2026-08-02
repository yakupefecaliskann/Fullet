import re
import sys
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from column_mapping import prices_from_row, resolve_fuel_columns
from http_utils import HTTP
from db_utils import finish_bot_run, normalize_city, save_regional_prices_to_supabase

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

BASE_URL = "https://www.tppd.com.tr"
SOURCE = "www.tppd.com.tr/akaryakit-fiyatlari"
HEADERS = {"User-Agent": "Mozilla/5.0 (Fullet fuel price monitor)"}


def _price_page_urls():
    response = HTTP.get(
        f"{BASE_URL}/akaryakit-fiyatlari",
        headers=HEADERS,
        timeout=(5, 30),
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    urls = []
    seen = set()
    # "-akaryakit-fiyatlari" son ekiyle eşleşen ama il sayfası OLMAYAN
    # bağlantılar (örn. /gecmis-akaryakit-fiyatlari) elenmeli; aksi halde
    # "GECMIS" sahte bir il gibi kazınıp boşa istek üretiyor.
    non_city_slugs = {"gecmis", "guncel", "tarihce"}
    for link in soup.select("a[href$='-akaryakit-fiyatlari']"):
        href = link.get("href")
        if not href:
            continue
        url = urljoin(BASE_URL, href)
        if url in seen or url == f"{BASE_URL}/akaryakit-fiyatlari":
            continue
        if _city_from_url(url).strip().lower().replace(" ", "-") in non_city_slugs:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def _city_from_url(url):
    slug = urlparse(url).path.strip("/").replace("-akaryakit-fiyatlari", "")
    return slug.replace("-", " ").strip()


def _city_from_page(soup, url):
    city = _city_from_url(url)
    if city:
        return city
    heading = soup.select_one("h1")
    if heading is None:
        return ""
    text = heading.get_text(" ", strip=True)
    return re.sub(r"\s+G[ÜU]NCEL\s+AKARYAKIT\s+F[Iİ]YATLARI$", "", text).strip()


def _parse_city_page(url):
    response = HTTP.get(url, headers=HEADERS, timeout=(5, 30))
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    city = _city_from_page(soup, url)
    if not city:
        return []

    table = soup.select_one("table")
    if table is None:
        return []

    rows = table.select("tr")
    if not rows:
        return []
    header_row = next((row for row in rows if row.find_all("th")), rows[0])
    header_cells = [
        cell.get_text(" ", strip=True) for cell in header_row.find_all(["th", "td"])
    ]
    # Sabit indeks yerine başlıktan çözüm. TP tablosunda iki ayrı "MOTORİN
    # (TL/LT)" kolonu var (ikisi de aynı değeri taşıyor) ve kilogram bazlı
    # ürünler (KALORİFER, FUEL OIL, Y.K. FUEL OIL) birim kapısıyla eleniyor.
    column_map = resolve_fuel_columns(header_cells)
    if not column_map:
        print(f"[WARN] TP {city}: yakıt kolonu eşleşmedi, sayfa atlandı.")
        return []

    parsed = []
    normalized_city = normalize_city(city)
    for row in rows[1:]:
        cols = [cell.get_text(" ", strip=True) for cell in row.select("td")]
        if len(cols) < 4:
            continue

        district = cols[0].strip()
        normalized_district = normalize_city(district)
        if not normalized_district or normalized_district == normalized_city:
            continue
        if re.match(r"^ISTANBUL\s*-\s*(ANADOLU|AVRUPA)$", normalized_district):
            continue

        prices = prices_from_row(cols, column_map)
        if not prices:
            continue

        parsed.append({
            "marka": "Türkiye Petrolleri",
            "il": city,
            "ilce": district,
            "fiyatlar": prices,
            "veri_kaynagi": SOURCE,
        })
    return parsed


def scrape_data():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Türkiye Petrolleri bot started.")
    scraped_data = []

    try:
        urls = _price_page_urls()
        print(f"[INFO] TP price pages: {len(urls)}")
        for url in urls:
            scraped_data.extend(_parse_city_page(url))
    except Exception as exc:
        print(f"[WARN] Türkiye Petrolleri scrape failed: {exc}")

    return scraped_data


if __name__ == "__main__":
    start_time = datetime.now()
    data = scrape_data()
    summary = save_regional_prices_to_supabase(data, default_brand="Türkiye Petrolleri")
    print(f"[OK] Türkiye Petrolleri finished in {(datetime.now() - start_time).total_seconds():.1f}s.")
    raise SystemExit(finish_bot_run("tp_bot.py", scraped=len(data), summary=summary))
