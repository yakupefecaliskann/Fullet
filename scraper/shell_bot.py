import asyncio
import os
from datetime import datetime, timezone

from playwright.async_api import async_playwright

from db_utils import normalize_city, parse_price, save_regional_prices_to_supabase, supabase

TARGET_LOCATIONS = [
    {"il": "ISTANBUL", "ilce": "KADIKOY"},
    {"il": "ANKARA", "ilce": "CANKAYA"},
    {"il": "IZMIR", "ilce": "KONAK"},
]

DEFAULT_MAX_TARGETS_PER_RUN = 0  # 0 = sınırsız, tüm hedefler
N_PARALLEL_WORKERS = 5

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
    return [targets[key] for key in sorted(targets)]


def _limited_targets(target_locations):
    if not target_locations:
        return target_locations
    max_targets = int(os.environ.get("SHELL_MAX_TARGETS_PER_RUN", DEFAULT_MAX_TARGETS_PER_RUN))
    if max_targets <= 0 or len(target_locations) <= max_targets:
        return target_locations

    explicit_offset = os.environ.get("SHELL_TARGET_OFFSET")
    if explicit_offset is not None:
        offset = int(explicit_offset) % len(target_locations)
    else:
        six_hour_window = int(datetime.now(timezone.utc).timestamp() // (6 * 60 * 60))
        offset = (six_hour_window * max_targets) % len(target_locations)

    rotated = target_locations[offset:] + target_locations[:offset]
    selected = rotated[:max_targets]
    print(
        f"[INFO] Shell target batch: {len(selected)}/{len(target_locations)} "
        f"(offset={offset}, max={max_targets})"
    )
    return selected


def _price_at(cols, index):
    return parse_price(cols[index]) if len(cols) > index else None


def _prices_from_row(cols):
    return {
        "Kursunsuz 95": _price_at(cols, 4) or _price_at(cols, 3),
        "Motorin": _price_at(cols, 5) or _price_at(cols, 6),
        "LPG": _price_at(cols, 12) or _price_at(cols, 10),
    }


async def _scrape_location(page, city, district):
    """Tek il/ilçe kombinasyonunu async scrape eder."""
    try:
        await page.locator("#cb_all_cb_province_B-1Img").click(force=True)
        await page.wait_for_timeout(750)
        city_loc = page.locator(
            f"#cb_all_cb_province_DDD_L_LBT td:has-text('{city}')"
        ).first
        if await city_loc.count() > 0:
            await city_loc.click(force=True)
            await page.wait_for_timeout(1000)
        else:
            await page.keyboard.press("Escape")
            return []

        await page.locator("#cb_all_cb_county_B-1Img").click(force=True)
        await page.wait_for_timeout(750)
        dist_loc = page.locator(
            f"#cb_all_cb_county_DDD_L_LBT td:has-text('{district}')"
        ).first
        if await dist_loc.count() > 0:
            await dist_loc.click(force=True)
            await page.wait_for_timeout(1000)
        else:
            await page.keyboard.press("Escape")
            return []

        await page.locator("#cb_all_ASPxButton1_CD").click(force=True)

        try:
            await page.wait_for_selector(
                "#cb_all_grdPrices_LD", state="hidden", timeout=20000
            )
            await page.wait_for_selector(
                ".dxeLoadingDivWithContent", state="hidden", timeout=5000
            )
        except Exception as exc:
            print(f"[WARN] {city}/{district} loading: {exc}")

        await page.wait_for_timeout(1500)

        rows = await page.locator(
            "#cb_all_grdPrices_DXMainTable tr.dxgvDataRow"
        ).all()
        results = []
        for row in rows:
            cols = await row.locator("td").all_inner_texts()
            if len(cols) < 13:
                continue
            station_district = cols[2].strip()
            prices = _prices_from_row(cols)
            prices = {f: p for f, p in prices.items() if p is not None}
            if not prices:
                continue
            results.append({
                "marka": "Shell",
                "il": city,
                "ilce": station_district,
                "fiyatlar": prices,
                "veri_kaynagi": "turkiyeshell.com/pompatest/History.aspx",
            })
        print(f"[INFO] {city}/{district}: {len(results)} satır")
        return results
    except Exception as exc:
        print(f"[WARN] Shell scrape {city}/{district}: {exc}")
        return []


async def _scrape_batch(targets_batch, batch_id):
    """Ayrı async_playwright context ile bir batch işler."""
    batch_results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(
                "https://www.turkiyeshell.com/pompatest/History.aspx", timeout=60000
            )
            for loc in targets_batch:
                results = await _scrape_location(page, loc["il"], loc["ilce"])
                batch_results.extend(results)
        except Exception as exc:
            print(f"[WARN] Batch {batch_id} error: {exc}")
        finally:
            await browser.close()
    print(f"[INFO] Batch {batch_id} tamamlandı: {len(batch_results)} satır")
    return batch_results


async def _run_all(target_locations):
    n_workers = min(N_PARALLEL_WORKERS, len(target_locations))
    batches = [target_locations[i::n_workers] for i in range(n_workers)]
    results = await asyncio.gather(
        *[_scrape_batch(batch, i) for i, batch in enumerate(batches)],
        return_exceptions=True,
    )
    all_data = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"[WARN] Batch {i} failed: {result}")
        else:
            all_data.extend(result)
    return all_data


def scrape_shell_data(target_locations=None):
    target_locations = target_locations or _targets_from_supabase() or TARGET_LOCATIONS
    target_locations = _limited_targets(target_locations)
    n_workers = min(N_PARALLEL_WORKERS, len(target_locations))
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Shell bot started.")
    print(f"[INFO] {len(target_locations)} hedef, {n_workers} async worker")
    return asyncio.run(_run_all(target_locations))


if __name__ == "__main__":
    start_time = datetime.now()
    data = scrape_shell_data()
    save_regional_prices_to_supabase(data, default_brand="Shell")
    print(f"[OK] Shell finished in {(datetime.now() - start_time).total_seconds():.1f}s.")
