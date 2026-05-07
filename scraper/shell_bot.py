from datetime import datetime

from playwright.sync_api import sync_playwright

from db_utils import normalize_city, parse_price, save_regional_prices_to_supabase, supabase

TARGET_LOCATIONS = [
    {"il": "ISTANBUL", "ilce": "KADIKOY"},
    {"il": "ANKARA", "ilce": "CANKAYA"},
    {"il": "IZMIR", "ilce": "KONAK"},
]

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


def scrape_shell_data(target_locations=None):
    target_locations = target_locations or _targets_from_supabase() or TARGET_LOCATIONS
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Shell bot started.")
    print(f"[INFO] Shell targets: {len(target_locations)}")
    scraped_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto("https://www.turkiyeshell.com/pompatest/History.aspx", timeout=60000)

            for loc in target_locations:
                city = loc["il"]
                district = loc["ilce"]
                print(f"[INFO] Shell target: {city} / {district}")

                page.locator("#cb_all_cb_province_B-1Img").click()
                page.wait_for_timeout(700)
                city_locator = page.locator(f"#cb_all_cb_province_DDD_L_LBT td:has-text('{city}')").first
                if city_locator.is_visible():
                    city_locator.click()
                    page.wait_for_timeout(1500)
                else:
                    page.keyboard.press("Escape")
                    continue

                page.locator("#cb_all_cb_county_B-1Img").click()
                page.wait_for_timeout(700)
                district_locator = page.locator(f"#cb_all_cb_county_DDD_L_LBT td:has-text('{district}')").first
                if district_locator.is_visible():
                    district_locator.click()
                    page.wait_for_timeout(1500)
                else:
                    page.keyboard.press("Escape")
                    continue

                page.locator("#cb_all_ASPxButton1_CD").click()
                page.wait_for_timeout(2500)

                rows = page.locator("#cb_all_grdPrices_DXMainTable tr.dxgvDataRow").all()
                print(f"[INFO] {len(rows)} Shell rows found.")

                for row in rows:
                    cols = row.locator("td").all_inner_texts()
                    if len(cols) < 13:
                        continue

                    station_district = cols[2].strip()
                    prices = {
                        "Kursunsuz 95": parse_price(cols[4]) or parse_price(cols[3]),
                        "Motorin": parse_price(cols[6]) or parse_price(cols[5]),
                        "LPG": parse_price(cols[12]) or parse_price(cols[10]),
                    }
                    prices = {fuel: price for fuel, price in prices.items() if price is not None}
                    if not prices:
                        continue

                    scraped_data.append({
                        "marka": "Shell",
                        "il": city,
                        "ilce": station_district,
                        "fiyatlar": prices,
                        "veri_kaynagi": "turkiyeshell.com/pompatest/History.aspx",
                    })
        except Exception as exc:
            print(f"[WARN] Shell scrape failed: {exc}")
        finally:
            browser.close()

    return scraped_data


if __name__ == "__main__":
    start_time = datetime.now()
    data = scrape_shell_data()
    save_regional_prices_to_supabase(data, default_brand="Shell")
    print(f"[OK] Shell finished in {(datetime.now() - start_time).total_seconds():.1f}s.")
