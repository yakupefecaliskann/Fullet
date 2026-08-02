import re
import sys
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from http_utils import HTTP
from db_utils import finish_bot_run, normalize_city, parse_price, save_regional_prices_to_supabase

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
    for link in soup.select("a[href$='-akaryakit-fiyatlari']"):
        href = link.get("href")
        if not href:
            continue
        url = urljoin(BASE_URL, href)
        if url in seen or url == f"{BASE_URL}/akaryakit-fiyatlari":
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

    parsed = []
    normalized_city = normalize_city(city)
    for row in table.select("tr")[1:]:
        cols = [cell.get_text(" ", strip=True) for cell in row.select("td")]
        if len(cols) < 4:
            continue

        district = cols[0].strip()
        normalized_district = normalize_city(district)
        if not normalized_district or normalized_district == normalized_city:
            continue
        if re.match(r"^ISTANBUL\s*-\s*(ANADOLU|AVRUPA)$", normalized_district):
            continue

        prices = {
            "Kursunsuz 95": parse_price(cols[1]),
            "Motorin": parse_price(cols[3]),
        }
        if len(cols) > 8:
            prices["LPG"] = parse_price(cols[8])
        prices = {
            fuel: price
            for fuel, price in prices.items()
            if price is not None
        }
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
