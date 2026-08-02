import sys
from datetime import datetime

from bs4 import BeautifulSoup

from column_mapping import describe_column_map, prices_from_row, resolve_fuel_columns
from http_utils import HTTP
from db_utils import finish_bot_run, save_to_supabase

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def _header_cells(table):
    """Tablonun başlık satırındaki metinleri döner (th varsa th, yoksa ilk tr)."""
    rows = table.select("tr")
    if not rows:
        return []
    header_row = next((row for row in rows if row.find_all("th")), rows[0])
    return [
        cell.get_text(" ", strip=True)
        for cell in header_row.find_all(["th", "td"])
    ]


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

        table = soup.select_one("table")
        if table is None:
            print("[WARN] BP: fiyat tablosu bulunamadı.")
            return scraped_data

        # BP tablosu PO'dan farklı kolon sayısına sahip (Ultimate ürünleri ayrı
        # kolonlarda). Sabit indeks yerine başlıktan çözüyoruz; "BP Ultimate"
        # kolonları premium sayılıp standart kolonlardan sonra denenir.
        column_map = resolve_fuel_columns(_header_cells(table))
        print(f"[INFO] BP kolon eşlemesi: {describe_column_map(column_map)}")
        if not column_map:
            print("[WARN] BP: yakıt kolonu eşleşmedi, kazıma durduruldu.")
            return scraped_data

        rows = table.select("tr")
        for row in rows:
            cols = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
            if len(cols) < 3:
                continue
            if cols[0].lower() in ("şehir", "sehir"):
                continue

            city = cols[0]
            prices = prices_from_row(cols, column_map)
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
    summary = save_to_supabase(data, default_brand="BP")
    print(f"[OK] BP finished in {(datetime.now() - start_time).total_seconds():.1f}s.")
    raise SystemExit(finish_bot_run("bp_bot.py", scraped=len(data), summary=summary))
