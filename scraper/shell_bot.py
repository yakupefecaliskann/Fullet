import os
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

from column_mapping import describe_column_map, prices_from_row, resolve_fuel_columns
from db_utils import finish_bot_run, normalize_city, parse_price, save_regional_prices_to_supabase, supabase
from normalization import PROVINCES

TARGET_LOCATIONS = [
    {"il": "ISTANBUL", "ilce": "KADIKOY"},
    {"il": "ANKARA", "ilce": "CANKAYA"},
    {"il": "IZMIR", "ilce": "KONAK"},
]

DEFAULT_MAX_TARGETS_PER_RUN = 150

LOCATION_FIXES = {
    ("BUYUKKARISTIRAN", "LULEBURGAZ"): ("KIRKLARELI", "LULEBURGAZ"),
    ("MILAS", "MUGLA"): ("MUGLA", "MILAS"),
    ("MUREFTE", "SARKOY"): ("TEKIRDAG", "SARKOY"),
    ("TOPAGAC", "SULEYMANPASA"): ("TEKIRDAG", "SULEYMANPASA"),
    ("YATAGAN", "MUGLA"): ("MUGLA", "YATAGAN"),
}


def _split_city(raw_city, raw_district):
    city = normalize_city(raw_city)
    district = normalize_city(raw_district)
    if "/" in city:
        left, right = [part.strip() for part in city.split("/", 1)]
        city = right
        if not district:
            district = left
    if district.endswith(" MERKEZ") or district.startswith("MERKEZ "):
        district = "MERKEZ"
    city, district = LOCATION_FIXES.get((city, district), (city, district))
    if city not in PROVINCES and district in PROVINCES:
        city, district = district, city
    return city, district


_PRIORITY_CITIES = frozenset({"ISTANBUL", "ANKARA", "IZMIR"})


def _targets_from_supabase():
    if supabase is None:
        return []
    rows = (
        supabase.table("istasyonlar")
        .select("il,ilce")
        .eq("marka", "Shell")
        .not_.is_("il", "null")
        .execute()
        .data
        or []
    )
    targets = {}
    for row in rows:
        city, district = _split_city(row.get("il"), row.get("ilce"))
        if not city or not district:
            continue
        if district in {"BILINMIYOR", "TURKIYE"}:
            continue
        if city in {"BILINMIYOR", "TURKIYE"}:
            continue
        if city not in PROVINCES:
            continue
        targets[(city, district)] = {"il": city, "ilce": district}
    # Priority cities (Istanbul, Ankara, Izmir) always go first so they're
    # covered in every rotation window regardless of offset.
    priority = [targets[k] for k in sorted(targets) if k[0] in _PRIORITY_CITIES]
    others = [targets[k] for k in sorted(targets) if k[0] not in _PRIORITY_CITIES]
    return priority + others


def _limited_targets(target_locations):
    if not target_locations:
        return target_locations
    max_targets = int(os.environ.get("SHELL_MAX_TARGETS_PER_RUN", DEFAULT_MAX_TARGETS_PER_RUN))
    if max_targets <= 0 or len(target_locations) <= max_targets:
        return target_locations

    # Priority cities always fill the front of the batch; rotation applies only to others.
    priority = [loc for loc in target_locations if loc["il"] in _PRIORITY_CITIES]
    others = [loc for loc in target_locations if loc["il"] not in _PRIORITY_CITIES]
    remaining_slots = max(0, max_targets - len(priority))

    explicit_offset = os.environ.get("SHELL_TARGET_OFFSET")
    if explicit_offset is not None:
        offset = int(explicit_offset) % max(len(others), 1)
    else:
        six_hour_window = int(datetime.now(timezone.utc).timestamp() // (6 * 60 * 60))
        offset = (six_hour_window * remaining_slots) % max(len(others), 1)

    rotated = others[offset:] + others[:offset]
    selected = priority + rotated[:remaining_slots]
    print(
        f"[INFO] Shell target batch: {len(selected)}/{len(target_locations)} "
        f"(priority={len(priority)}, other={remaining_slots}, offset={offset}, max={max_targets})"
    )
    return selected


def _price_at(cols, index):
    return parse_price(cols[index]) if len(cols) > index else None


# Shell grid'inin sabit kolon indeksleriyle okunması, projenin en pahalı veri
# hatasıydı: "LPG": _price_at(12) or _price_at(10). Kolon 12 gerçek Otogaz'dır
# ama çoğu ilçede boştur ("-"); `or` fallback'i devreye girip kolon 10'u —
# "Yüksek Kükürtlü Fuel Oil (TL/Kg)" — LPG diye yazıyordu. Kilogram başına
# fuel oil fiyatı (38,51), litre başına LPG olarak kaydedildi ve Shell LPG
# ortalamasını diğer markalardan %20 yukarı çekti (37,68 vs ~31,3).
# Artık kolonlar başlık metninden çözülüyor (column_mapping.py) ve fallback
# yalnızca AYNI yakıtın kolonları arasında yapılıyor.
SHELL_HEADER_SELECTOR = "#cb_all_grdPrices td.dxgvHeader, #cb_all_grdPrices th.dxgvHeader"


def _read_column_map(page):
    """Grid başlıklarından yakıt->kolon eşlemesi okur. Başlıklar sorgular
    arasında değişmediği için ilk başarılı okumadan sonra tekrar okunmaz."""
    headers = page.locator(SHELL_HEADER_SELECTOR).all_inner_texts()
    if not headers:
        return None
    column_map = resolve_fuel_columns(headers)
    print(f"[INFO] Shell kolon eşlemesi: {describe_column_map(column_map)}")
    if "LPG" not in column_map:
        print("[WARN] Shell Otogaz kolonu başlıklarda bulunamadı — LPG yazılmayacak.")
    return column_map


def _prices_from_row(cols, column_map):
    return prices_from_row(cols, column_map, parse=parse_price)


# DevExpress combobox'ları grid callback'i sürerken DOM'da KALIR ama görünmez
# olur. Eski kod sabit 750 ms bekleyip `click(force=True)` çağırıyordu;
# `force` yalnızca "stable / receives events / enabled" kontrollerini atlar,
# GÖRÜNÜRLÜĞÜ atlamaz — bu yüzden yavaş callback'lerde Playwright
# "Element is not visible" fırlatıyor, hedef `except` tarafından yutuluyor ve
# bot yine exit 0 dönüyordu. Canlı ölçüm (8 koşu, bot_runs stdout'u):
# denenen ~44 hedefin ~28'i (%63) tam olarak böyle kayboluyordu.
# Çözüm: sabit uyku yerine görünürlük bekle, hedef bazında bir kez daha dene.
ELEMENT_TIMEOUT_MS = 15000
TARGET_MAX_ATTEMPTS = 2


def _settle(page):
    """Devam eden DevExpress callback'lerinin bitmesini bekler."""
    for selector in ("#cb_all_grdPrices_LD", ".dxeLoadingDivWithContent"):
        try:
            page.wait_for_selector(selector, state="hidden", timeout=ELEMENT_TIMEOUT_MS)
        except Exception:
            # Yükleme göstergesi hiç oluşmamış olabilir; bu bir hata değil.
            pass


class _OptionMissing(Exception):
    """Aranan il/ilçe açılır listede yok — tekrar denemek işe yaramaz."""


def _select_from_combo(page, button_selector, list_selector, value):
    button = page.locator(button_selector)
    button.wait_for(state="visible", timeout=ELEMENT_TIMEOUT_MS)
    button.click(force=True)

    option = page.locator(f"{list_selector} td:has-text('{value}')").first
    try:
        option.wait_for(state="visible", timeout=ELEMENT_TIMEOUT_MS)
    except Exception as exc:
        page.keyboard.press("Escape")
        raise _OptionMissing(value) from exc
    option.click(force=True)
    _settle(page)


def _scrape_target(page, city, district, column_map):
    """Tek bir il/ilçe hedefini okur. Döner: (satırlar, column_map)."""
    _settle(page)
    _select_from_combo(
        page, "#cb_all_cb_province_B-1Img", "#cb_all_cb_province_DDD_L_LBT", city
    )
    _select_from_combo(
        page, "#cb_all_cb_county_B-1Img", "#cb_all_cb_county_DDD_L_LBT", district
    )

    search = page.locator("#cb_all_ASPxButton1_CD")
    search.wait_for(state="visible", timeout=ELEMENT_TIMEOUT_MS)
    search.click(force=True)
    _settle(page)

    if column_map is None:
        column_map = _read_column_map(page)
    if not column_map:
        raise RuntimeError("kolon başlıkları okunamadı")

    rows = page.locator("#cb_all_grdPrices_DXMainTable tr.dxgvDataRow").all()
    print(f"[INFO] {len(rows)} Shell rows found.")
    scraped = []
    for row in rows:
        cols = row.locator("td").all_inner_texts()
        if len(cols) < 13:
            continue
        prices = _prices_from_row(cols, column_map)
        if not prices:
            continue
        scraped.append({
            "marka": "Shell",
            "il": city,
            "ilce": cols[2].strip(),
            "fiyatlar": prices,
            "veri_kaynagi": "turkiyeshell.com/pompatest/History.aspx",
        })
    return scraped, column_map


def scrape_shell_data(target_locations=None):
    """Döner: (kayıtlar, kapsama istatistikleri).

    İstatistikler `finish_bot_run`'a gider: hedeflerin çoğu kaybolduğunda koşu
    artık sessizce 'success' görünmüyor.
    """
    target_locations = target_locations or _targets_from_supabase() or TARGET_LOCATIONS
    target_locations = _limited_targets(target_locations)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Shell bot started.")
    print(f"[INFO] Shell targets: {len(target_locations)}")
    scraped_data = []
    column_map = None
    stats = {"attempted": 0, "ok": 0, "missing": 0, "failed": 0}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("https://www.turkiyeshell.com/pompatest/History.aspx", timeout=60000)
            for loc in target_locations:
                city = loc["il"]
                district = loc["ilce"]
                print(f"[INFO] Shell target: {city} / {district}")
                stats["attempted"] += 1
                last_error = None
                for attempt in range(TARGET_MAX_ATTEMPTS):
                    try:
                        rows, column_map = _scrape_target(page, city, district, column_map)
                        scraped_data.extend(rows)
                        stats["ok"] += 1
                        last_error = None
                        break
                    except _OptionMissing:
                        # İl/ilçe listede yok: istasyon envanterindeki değer
                        # Shell'in kendi listesiyle uyuşmuyor (ör. mahalle adı
                        # ilçe kolonuna yazılmış). Tekrar denemek anlamsız.
                        print(f"[MISS] {city}/{district}: listede yok.")
                        stats["missing"] += 1
                        last_error = None
                        break
                    except Exception as exc:
                        last_error = exc
                        if attempt + 1 < TARGET_MAX_ATTEMPTS:
                            print(f"[RETRY] {city}/{district}: {exc}")
                            _settle(page)
                if last_error is not None:
                    print(f"[WARN] Shell scrape {city}/{district}: {last_error}")
                    stats["failed"] += 1
        except Exception as exc:
            print(f"[WARN] Shell scrape failed: {exc}")
        finally:
            browser.close()

    print(
        f"[INFO] Shell hedef sonucu: ok={stats['ok']} "
        f"listede-yok={stats['missing']} hata={stats['failed']} "
        f"denenen={stats['attempted']}"
    )
    return scraped_data, stats


if __name__ == "__main__":
    start_time = datetime.now()
    data, stats = scrape_shell_data()
    summary = save_regional_prices_to_supabase(data, default_brand="Shell")
    print(f"[OK] Shell finished in {(datetime.now() - start_time).total_seconds():.1f}s.")
    raise SystemExit(
        finish_bot_run(
            "shell_bot.py",
            scraped=len(data),
            summary=summary,
            targets_ok=stats["ok"],
            targets_total=stats["attempted"],
        )
    )
