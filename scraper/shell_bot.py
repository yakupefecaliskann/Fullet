import os
import time
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
    # SAYFALAMA ŞART: PostgREST tek istekte en fazla 1000 satır döndürür ve
    # bunu SESSİZCE yapar. Shell'in 1414 istasyonu var; sayfalamasız sorgu
    # 414'ünü hiç görmüyordu, dolayısıyla o il/ilçeler hedef listesine hiç
    # girmiyor ve fiyatları HİÇ tazelenmiyordu (canlı kanıt: 152 istasyon
    # 30+ gündür doğrulanmamış, en eskisi 18 Nis 2026). Üstelik kapsama
    # oranının paydası da eksik kalıyordu — yani "%91 kapsama" gerçekte
    # olduğundan iyi görünüyordu. Depodaki diğer sorgular (ops_report,
    # database_writes) zaten bu range() kalıbını kullanıyor.
    rows = []
    start = 0
    while True:
        page = (
            supabase.table("istasyonlar")
            .select("il,ilce")
            .eq("marka", "Shell")
            .not_.is_("il", "null")
            .range(start, start + 999)
            .execute()
            .data
            or []
        )
        rows.extend(page)
        if len(page) < 1000:
            break
        start += 1000
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
    arasında değişmediği için ilk başarılı okumadan sonra tekrar okunmaz.

    Başlıkların DOM'a girmesi BEKLENİR: koşunun ilk aramasında grid henüz
    boştur ve beklemeden okuyan kod ilk hedefi iki denemede de kaybediyordu
    (canlı log: "[WARN] ANKARA/ALTINDAG: kolon başlıkları okunamadı").
    """
    try:
        page.wait_for_selector(
            SHELL_HEADER_SELECTOR, state="attached", timeout=GRID_TIMEOUT_MS
        )
    except Exception:
        # Beklemenin başarısızlığı tek başına hata değil; asıl karar
        # aşağıdaki boş başlık kontrolünde veriliyor.
        pass
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

# Açılır liste, düğmeye tıklandıktan sonra hızlıca render edilir. Bir ilçenin
# listede OLUP OLMADIĞINI anlamak için 15 saniye beklemek pahalı bir hataydı:
# Shell'in listesinde gerçekten bulunmayan ilçeler (envanterde mahalle adı
# ilçe kolonuna yazılmış kayıtlar: "HOROZLUHAN MAH Y", "MASLAK", "ISKITLER")
# eski kodda `.count() > 0` ile ANINDA eleniyordu. 15 saniyelik bekleme,
# 150 hedeflik koşuyu 9 dakikadan ~25 dakikaya çıkarıp 1800 sn'lik subprocess
# bütçesini deldi. Yokluk kararı 3 saniyede verilebilir; asıl kırılganlık olan
# combobox DÜĞMESİNİN görünürlüğü uzun timeout'u hak eder.
OPTION_TIMEOUT_MS = 3000

# Açılır listenin açılmasını bekleme süresi.
COMBO_OPEN_TIMEOUT_MS = 4000

# Açılır liste görünür olduktan sonra DevExpress popup'ı hâlâ konumlanıyor
# olabilir. `click(force=True)` tam da bu "stable" kontrolünü atladığı için
# tıklama, popup'ın bir an sonra terk ettiği koordinata gidiyor ve SESSİZCE
# hiçbir şey seçmiyordu (bkz. _select_verified). Konumun oturmasını ölçerek
# bekliyoruz; ölçüm 2 sn'yi hiç aşmadı.
POPUP_SETTLE_TIMEOUT_MS = 2000
POPUP_SETTLE_POLL_MS = 80

# Seçim sonrası combobox'ın GERÇEKTEN hedefe geçtiğini doğrulama süresi.
SELECT_VERIFY_TIMEOUT_MS = 4000
SELECT_ATTEMPTS = 3
DROPDOWN_CLOSE_TIMEOUT_MS = 3000

# İl seçimi sonrası ilçe listesinin cascade callback'iyle yenilenme süresi.
# CANLI ÖLÇÜM (6 il, 3 Ağu 2026): cascade 0,11–0,35 sn sürüyor. Buradaki 10 sn
# cömert bir üst sınırdır; aşılıyorsa gerçekten bir şey bozulmuştur.
COUNTY_CASCADE_TIMEOUT_MS = 10000
COUNTY_CASCADE_POLL_MS = 100

# Hedefe BAŞLAMADAN önceki "yatışma" kritik değil; önceki callback zaten
# bitmiş olabilir, uzun timeout burada boşa harcanır.
SETTLE_TIMEOUT_MS = 5000

# ARAMA sonrası grid yüklemesi ise kritik: erken dönersek bir önceki ilçenin
# satırlarını okur ya da boş grid görürüz. Orijinal kodun 20 sn'lik değeri
# korunur — bu bekleme kısaltılamaz.
GRID_TIMEOUT_MS = 20000

# Yükleme göstergesinin kaybolması, grid'in YENİ ilin satırlarıyla dolduğu
# anlamına GELMİYOR. Canlı ölçüm (3 Ağu, 150 hedef): kalan 19 hatanın 18'i
# tam olarak buydu ve hepsi bir ilin İLK hedefiydi — arama sonrası grid hâlâ
# önceki ilin satırlarını gösteriyordu. Doğru sinyal göstergenin durumu değil,
# grid'in kendi İl kolonudur.
GRID_MATCH_TIMEOUT_MS = 10000
GRID_POLL_MS = 150

TARGET_MAX_ATTEMPTS = 2

# Duvar saati bütçesi. run_all_bots shell_bot'u 1800 sn'de ÖLDÜRÜR; öldürülen
# süreç `[RECORDS]` satırını hiç basamaz, yani görünür kılmaya çalıştığımız
# kapsama verisi tam da en çok ihtiyaç duyulan anda kaybolur (status yalnızca
# 'timeout' olur, "kaç hedef okundu" bilinmez). Bot kendi bütçesini yönetip
# temiz çıkar ve dürüst sayıları raporlar.
RUN_BUDGET_SECONDS = int(os.environ.get("SHELL_RUN_BUDGET_SECONDS", 1500))


def _settle(page, timeout=SETTLE_TIMEOUT_MS):
    """Devam eden DevExpress callback'lerinin bitmesini bekler."""
    for selector in ("#cb_all_grdPrices_LD", ".dxeLoadingDivWithContent"):
        try:
            page.wait_for_selector(selector, state="hidden", timeout=timeout)
        except Exception:
            # Yükleme göstergesi hiç oluşmamış olabilir; bu bir hata değil.
            pass


class _OptionMissing(Exception):
    """Aranan il/ilçe açılır listede yok — tekrar denemek işe yaramaz."""


# Sayfa, DevExpress combobox'larını global olarak yayınlıyor
# (`window['cb_province']`, `window['cb_county']`). Bu nesneler seçimin
# GERÇEKTEN olup olmadığını söyleyen tek güvenilir kaynaktır: DOM'a bakarak
# "tıkladım, olmuştur" varsaymak zorunda kalmayız.
PROVINCE_COMBO = "cb_province"
COUNTY_COMBO = "cb_county"
PROVINCE_BUTTON = "#cb_all_cb_province_B-1Img"
PROVINCE_LIST_SELECTOR = "#cb_all_cb_province_DDD_L_LBT"
COUNTY_BUTTON = "#cb_all_cb_county_B-1Img"
COUNTY_LIST_SELECTOR = "#cb_all_cb_county_DDD_L_LBT"

_JS_COMBO_TEXT = "(name) => window[name] ? window[name].GetText() : null"
_JS_COMBO_ITEMS = """(name) => {
    const combo = window[name];
    if (!combo) return [];
    const out = [];
    for (let i = 0; i < combo.GetItemCount(); i++) {
        const item = combo.GetItem(i);
        out.push(item ? item.text : "");
    }
    return out;
}"""
_JS_HIDE_DROPDOWN = """(name) => {
    try { if (window[name]) window[name].HideDropDown(); } catch (e) {}
}"""


def _combo_text(page, combo):
    """Combobox'ta O AN seçili olan metin (seçimin tek doğrulanabilir kanıtı)."""
    try:
        return page.evaluate(_JS_COMBO_TEXT, combo)
    except Exception:
        return None


def _combo_items(page, combo):
    try:
        return page.evaluate(_JS_COMBO_ITEMS, combo) or []
    except Exception:
        return []


def _close_dropdown(page, combo, list_selector):
    """Açılır listeyi KAPALI duruma getirir.

    Düğmeye tıklamak bir TOGGLE'dır: liste zaten açıkken tıklamak onu kapatır.
    Eski kod her seferinde körlemesine tıkladığı için açık/kapalı durum
    kayıyordu ve seçimler "bir il geriden" geliyordu. Bilinen bir durumdan
    başlamak bu sınıf hatayı tamamen ortadan kaldırır.
    """
    try:
        page.evaluate(_JS_HIDE_DROPDOWN, combo)
    except Exception:
        pass
    try:
        page.locator(list_selector).wait_for(
            state="hidden", timeout=DROPDOWN_CLOSE_TIMEOUT_MS
        )
    except Exception:
        pass


def _wait_popup_settled(page, list_selector, timeout=POPUP_SETTLE_TIMEOUT_MS):
    """Popup'ın konumu iki ardışık ölçümde aynı olana kadar bekler.

    `click(force=True)`in atladığı "stable" kontrolünün elle yapılmış hâli.
    Bu bekleme olmadan tıklama, popup'ın bir an sonra terk ettiği koordinata
    gidiyor ve hiçbir istisna fırlatmadan HİÇBİR ŞEY seçmiyor.
    """
    locator = page.locator(list_selector)
    deadline = time.monotonic() + timeout / 1000
    previous = None
    while time.monotonic() < deadline:
        try:
            box = locator.bounding_box()
        except Exception:
            return
        if box is not None and box == previous:
            return
        previous = box
        page.wait_for_timeout(POPUP_SETTLE_POLL_MS)


def _select_verified(page, combo, button_selector, list_selector, value):
    """Açılır listeden seçer ve seçimin TUTTUĞUNU doğrular; tutmadıysa tekrarlar.

    Bu botun en pahalı hatası "tıkladım, olmuştur" varsayımıydı. Canlı ölçüm
    (3 Ağu 2026): ANKARA'dan sonraki il seçimleri sessizce boşa gidiyordu —
    istisna yok, ağ isteği yok, `cb_province.GetText()` hâlâ önceki il. Sonuç,
    ilçe listesinin "bir il geriden gelmesi"ydi; oysa liste DOĞRUYDU, seçilen
    il yanlıştı. Teşhisi 3 kez ıskalamamızın sebebi buydu.

    İki kural: (1) tıklamadan önce popup'ın konumu otursun, (2) combobox'ın
    kendi değeri hedefe eşit olmadan ASLA devam etme.
    """
    for _ in range(SELECT_ATTEMPTS):
        if normalize_city(_combo_text(page, combo) or "") == value:
            return
        _close_dropdown(page, combo, list_selector)
        button = page.locator(button_selector)
        button.wait_for(state="visible", timeout=ELEMENT_TIMEOUT_MS)
        button.click(force=True)
        try:
            page.locator(list_selector).wait_for(
                state="visible", timeout=COMBO_OPEN_TIMEOUT_MS
            )
        except Exception:
            continue
        _wait_popup_settled(page, list_selector)

        # Metinleri okuyup İKİ TARAFI DA normalize ederek eşleştir.
        # `td:has-text('ARNAVUTKOY')` büyük/küçük harfe duyarsızdır ama AKSANA
        # DUYARLIDIR: hedeflerimiz ASCII (`normalize_city`), Shell'in listesi
        # Türkçe yazıyor (ARNAVUTKÖY, ATAŞEHİR, KÂĞITHANE...). Normalize
        # edilmiş TAM eşleşme ayrıca "YENI" -> "YENIMAHALLE" gibi alt dize
        # yanlış hedeflerini de engeller.
        cells = page.locator(f"{list_selector} td")
        options = [normalize_city(text) for text in cells.all_inner_texts()]
        if value not in options:
            _close_dropdown(page, combo, list_selector)
            raise _OptionMissing(value)

        option = cells.nth(options.index(value))
        try:
            # Kaydırma olmadan tıklama "Element is outside of the viewport" verir.
            option.scroll_into_view_if_needed(timeout=OPTION_TIMEOUT_MS)
            # force YOK: Playwright'ın stabilite ve hit-test kontrolleri tam da
            # burada gerekiyor. Hata olursa aşağıdaki doğrulama yakalar.
            option.click(timeout=OPTION_TIMEOUT_MS)
        except Exception:
            pass

        deadline = time.monotonic() + SELECT_VERIFY_TIMEOUT_MS / 1000
        while time.monotonic() < deadline:
            if normalize_city(_combo_text(page, combo) or "") == value:
                return
            page.wait_for_timeout(100)

    raise RuntimeError(
        f"seçim doğrulanamadı: {value} (combobox='{_combo_text(page, combo)}')"
    )


GRID_ROW_SELECTOR = "#cb_all_grdPrices_DXMainTable tr.dxgvDataRow"

_JS_GRID_FIRST_CITY = """(selector) => {
    const row = document.querySelector(selector);
    if (!row) return null;
    const cells = row.querySelectorAll("td");
    return cells.length > 1 ? cells[1].innerText : null;
}"""


def _wait_for_grid(page, city, timeout=GRID_MATCH_TIMEOUT_MS):
    """Grid'in SEÇİLEN İLE ait satırları göstermesini bekler.

    `_settle` yalnızca yükleme göstergesinin kaybolmasını bekliyor; gösterge
    daha belirmeden okursak grid hâlâ ÖNCEKİ ilin satırlarını içeriyor.
    Boş grid'de erken dönmek yok: satırlar bir an silinip yeniden doluyor
    olabilir, o aralıkta "kayıt yok" demek sessiz bir eksik sayımdır.
    """
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        try:
            grid_city = page.evaluate(_JS_GRID_FIRST_CITY, GRID_ROW_SELECTOR)
        except Exception:
            return False
        if grid_city and normalize_city(grid_city) == city:
            return True
        page.wait_for_timeout(GRID_POLL_MS)
    return False


def _wait_county_cascade(page, previous_items, timeout=COUNTY_CASCADE_TIMEOUT_MS):
    """İl DOĞRULANARAK seçildikten sonra ilçe listesinin yenilenmesini bekler.

    Cascade, History.aspx'e giden bir POST callback'i; canlı ölçümde
    0,11–0,35 sn sürüyor (6 il). Yani "cascade yavaş" teşhisi baştan beri
    yanlıştı — liste geç gelmiyordu, il hiç seçilmemişti.

    Yine de beklemek şart: seçimden hemen sonra liste bir an ÖNCEKİ ilin
    ilçelerini gösterir ve o aralıkta okursak yanlış ilçe listesinde ararız.
    """
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        items = _combo_items(page, COUNTY_COMBO)
        if items and items != previous_items:
            return True
        page.wait_for_timeout(COUNTY_CASCADE_POLL_MS)
    return False


def _scrape_target(page, city, district, column_map, state):
    """Tek bir il/ilçe hedefini okur. Döner: (satırlar, column_map).

    `state` çağıran tarafından tutulan mutable sözlüktür: {"city": <seçili il>}.
    YALNIZCA il seçimi doğrulanıp cascade tamamlandıktan sonra güncellenir.

    Bu sıralama kritik: eski kod `state["city"]`i seçim denemesinden HEMEN
    sonra yazıyordu. İl seçimi tutmazsa hedef yeniden deneniyor, ikinci
    denemede `city == state["city"]` olduğu için il BİR DAHA HİÇ SEÇİLMİYOR
    ve o ildeki bütün hedefler önceki ilin ilçe listesinde aranıyordu.
    Üretim kanıtı (3 Ağu gece koşusu): ISTANBUL'un ilk hedefinde bir seçim
    kaçtı, ardından 40 İstanbul hedefinin TAMAMI "listede yok" sayıldı.
    Cascade hatası yaşayan 6 ilde 63 hedef bu şekilde kaybedildi.
    """
    _settle(page)
    # İl zaten seçiliyse tekrar seçme: hem cascade'i hem de ~2 sn'lik
    # etkileşimi boşuna tetiklemeyelim (hedefler il il sıralı).
    if city != state.get("city"):
        # Doğrulanana kadar "seçili il yok" say; yarıda kalırsa sonraki
        # hedefler ESKİ ilin ilçe listesini okumasın.
        state["city"] = None
        # Combobox ZATEN bu ili gösteriyor olabilir: hedef, il seçiminden
        # SONRAKİ bir aşamada hata almış olabilir (ör. ilk hedefte kolon
        # başlıkları henüz yoktur ve bir kez yeniden denenir). O durumda
        # yeni bir cascade tetiklenmez; listenin değişmesini beklemek
        # bütün ili boş yere kaybettirir.
        already_selected = (
            normalize_city(_combo_text(page, PROVINCE_COMBO) or "") == city
        )
        previous_counties = _combo_items(page, COUNTY_COMBO)
        _select_verified(
            page, PROVINCE_COMBO, PROVINCE_BUTTON, PROVINCE_LIST_SELECTOR, city
        )
        if already_selected:
            # Cascade daha önce tamamlanmış; tek gereken listenin dolu olması.
            if not _combo_items(page, COUNTY_COMBO):
                raise RuntimeError(f"ilçe listesi {city} için boş")
        elif not _wait_county_cascade(page, previous_counties):
            raise RuntimeError(f"ilçe listesi {city} için yenilenmedi")
        state["city"] = city

    # İlçe listesi artık DOĞRU ile ait olduğu için "listede yok" kararı
    # nihayet güvenilir: gerçekten Shell'in envanterinde olmayan kayıttır.
    _select_verified(page, COUNTY_COMBO, COUNTY_BUTTON, COUNTY_LIST_SELECTOR, district)

    search = page.locator("#cb_all_ASPxButton1_CD")
    search.wait_for(state="visible", timeout=ELEMENT_TIMEOUT_MS)
    search.click(force=True)
    # Grid yüklemesi kritik: erken dönmek bir önceki ilçenin satırlarını
    # okumaya yol açar (sessiz veri bozulması).
    _settle(page, timeout=GRID_TIMEOUT_MS)
    # Göstergenin kaybolması yetmez; grid'in bu İLE ait olduğunu gör.
    # Görmezsek yine de devam edilir: aşağıdaki İl kolonu kontrolü ya
    # satırları reddeder (hedef yeniden denenir) ya da grid gerçekten boştur.
    _wait_for_grid(page, city)

    if column_map is None:
        column_map = _read_column_map(page)
    if not column_map:
        raise RuntimeError("kolon başlıkları okunamadı")

    rows = page.locator(GRID_ROW_SELECTOR).all()
    print(f"[INFO] {len(rows)} Shell rows found.")
    scraped = []
    mismatched = 0
    for row in rows:
        cols = row.locator("td").all_inner_texts()
        if len(cols) < 13:
            continue
        # GÜVENLİK AĞI: grid'in kendi İl kolonunu (cols[1]) seçtiğimiz ille
        # doğrula. Cascade gecikirse yanlış ilin satırları döner ve eskiden
        # bunlar BİZİM etiketimizle ("il": city) yazılıyordu — sessiz veri
        # bozulması. Artık uyuşmayan satır yazılmaz.
        grid_city = normalize_city(cols[1])
        if grid_city and grid_city != city:
            mismatched += 1
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

    if mismatched:
        # Tüm satırlar başka ile aitse seçim tutmamıştır: yeniden denenmeli.
        if not scraped:
            raise RuntimeError(
                f"grid {city} yerine başka ilin {mismatched} satırını döndürdü"
            )
        print(f"[WARN] {city}: {mismatched} satır başka ile ait, atlandı.")
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
    # `planned`, bu koşuda kapsanması GEREKEN hedef sayısı; `attempted` ise
    # bütçe içinde sırası gelenler. Kapsama oranı planned'a göre hesaplanır —
    # aksi halde bütçe 40 hedefte kesilse ve 38'i okunsa "%95 kapsama" gibi
    # sahte bir rakam çıkar, oysa Shell'in yalnızca dörtte biri tazelenmiştir.
    state = {"city": None}
    stats = {
        "planned": len(target_locations),
        "attempted": 0, "ok": 0, "missing": 0, "failed": 0,
        "budget_exhausted": False,
    }
    deadline = time.monotonic() + RUN_BUDGET_SECONDS

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Uzun görünüm: il listesi 81 öğeli. Dar pencerede seçenekler görünüm
        # alanının dışında kalıyor ve her tıklama bir kaydırmaya bağımlı hâle
        # geliyor — kırılganlığı bedavaya azaltmanın en ucuz yolu.
        page = browser.new_page(viewport={"width": 1280, "height": 1600})
        try:
            page.goto("https://www.turkiyeshell.com/pompatest/History.aspx", timeout=60000)
            for loc in target_locations:
                if time.monotonic() >= deadline:
                    stats["budget_exhausted"] = True
                    print(
                        f"[BUDGET] {RUN_BUDGET_SECONDS}s doldu; kalan "
                        f"{stats['planned'] - stats['attempted']} hedef atlandı. "
                        "Temiz çıkılıyor (öldürülen süreç kapsama raporlayamaz)."
                    )
                    break
                city = loc["il"]
                district = loc["ilce"]
                print(f"[INFO] Shell target: {city} / {district}")
                stats["attempted"] += 1
                last_error = None
                for attempt in range(TARGET_MAX_ATTEMPTS):
                    try:
                        rows, column_map = _scrape_target(
                            page, city, district, column_map, state
                        )
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
                        # Sayfa tutarsız bir durumda kalmış olabilir: seçili
                        # ili unut ki sonraki deneme ili BAŞTAN seçsin. Bunu
                        # yapmamak tek bir hatayı bütün ile yayan hataydı.
                        state["city"] = None
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
        f"denenen={stats['attempted']} planlanan={stats['planned']}"
        + (" (BÜTÇE DOLDU)" if stats["budget_exhausted"] else "")
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
            # planned, attempted değil: bütçe kesintisi kapsamayı DÜŞÜRMELİ.
            targets_total=stats["planned"],
        )
    )
