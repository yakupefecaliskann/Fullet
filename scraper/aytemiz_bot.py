import re
import sys
from datetime import datetime

from bs4 import BeautifulSoup

from http_utils import HTTP
from db_utils import finish_bot_run, parse_price, save_to_supabase

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

# Yalnızca "68,91" / "68.91" gibi saf sayı hücrelerini fiyat sayar; başlık
# metinlerinin içindeki rakamları (95 Oktan, TL/lt) fiyat sanmaz.
_PRICE_TOKEN_RE = re.compile(r"^\d{1,3}[.,]\d{1,3}$")


def _is_price_token(token):
    return bool(_PRICE_TOKEN_RE.match((token or "").strip()))


def _parse_table_rows(soup):
    table = soup.select_one("table")
    if table is None:
        return

    tokens = table.get_text("\n", strip=True).split("\n")

    # Aytemiz tablosu hücre yapısı olarak ayrıştırılamıyor (bs4 tek blok metin
    # görüyor), bu yüzden token yürüyüşü korunuyor. Ama sihirli "6" sabitleri
    # kaldırıldı: satır genişliği ve veri başlangıcı tablodan ölçülüyor.
    #
    # parse_price burada kullanılamaz — başlık metni "Benzin (Aytemiz Optimum
    # Kurş. 95 Oktan) (TL/lt)" noktalama artıklarından 0,95 olarak
    # ayrıştırılıyor ve satır hizasını kaydırıyor. Saf sayı tokenı şart.
    boundaries = [
        index
        for index in range(len(tokens) - 1)
        if not _is_price_token(tokens[index]) and _is_price_token(tokens[index + 1])
    ]
    if not boundaries:
        return

    price_start = boundaries[0]
    row_width = (boundaries[1] - boundaries[0]) if len(boundaries) > 1 else 6

    index = price_start
    # Okunan en sağdaki kolon index+2 olduğu için yeterli koşul budur. Eski
    # "index + 5 < len(tokens)" koşulu tablonun SON satırını her zaman
    # düşürüyordu (yol haritası S1-3).
    while index + 2 < len(tokens):
        city = tokens[index]
        if not _is_price_token(tokens[index + 1]):
            index += 1
            continue
        yield [
            city,
            tokens[index + 1],
            tokens[index + 2],
        ]
        index += row_width


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
    summary = save_to_supabase(data, default_brand="Aytemiz")
    print(f"[OK] Aytemiz finished in {(datetime.now() - start_time).total_seconds():.1f}s.")
    raise SystemExit(finish_bot_run("aytemiz_bot.py", scraped=len(data), summary=summary))
