"""Shell resmi istasyon envanteri botu (F4-6).

Kaynak: find.shell.com istasyon bulucusu. Üç kademeli:
    1. /tr/fuel/locations/tr_TR            -> 516 bölge sayfası
    2. /tr/fuel/locations/<bolge>/tr_TR    -> bölgedeki istasyon bağlantıları
    3. /tr/fuel/<id>-<slug>/tr_TR          -> koordinat + tam adres

--- 25 AĞUSTOS 2026 ARIZASI ---------------------------------------------

Bot 09.08.2026'dan beri her hafta 0 kayıtla başarısız oluyordu. Sebep bir
regresyon değil, KAYNAĞIN BİÇİM DEĞİŞİKLİĞİ: find.shell.com Ağustos
başında Inertia.js'e geçti. Proplar artık HTML özniteliğinde değil:

    ESKİ:  <div data-react-props="{&quot;geographicListProps&quot;:...}">
    YENİ:  <script data-page="app" type="application/json">
               {"component":..., "props":{"geographicListProps":...}}
           </script>

Prop sözlüğünün İÇİ aynı kaldı — `geographicListProps.locations`,
`stationListProps.locations`, `location.lat/lng` alanlarının hepsi
yerinde. Kırılan yalnızca dış kabuktu.

Ariza 2 hafta boyunca fark edilmedi çünkü eski `_react_props` biçimi
tanımadığında SESSİZCE boş sözlük dönüyordu: günlükte "0 istasyon" yazıyor
ama sebebini söyleyen tek satır yoktu. Yeni `_page_props` bu durumda hata
fırlatır — bkz. docs/KOD_DENETIM_ARSIVI.md §D.

Güvenlik süzgeçleri `station_inventory_common`'da; gerekçesi orada yazılı.
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urljoin

import requests

from db_utils import finish_bot_run, save_station_inventory_to_supabase, supabase
from normalization import PROVINCES, normalize_city
from station_inventory_common import (
    en_yakin_metre,
    gecerli_konum,
    karantinada_mi,
    rapor_yaz,
    yakinlik_indeksleri,
)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

BASE_URL = "https://find.shell.com"
LOCATIONS_URL = f"{BASE_URL}/tr/fuel/locations/tr_TR"
SOURCE = "find.shell.com/tr/fuel"
BRAND = "Shell"
HEADERS = {"User-Agent": "Mozilla/5.0 (Fullet official station inventory)"}
MAX_WORKERS = 12

# Kaynağın 1.289 istasyon listelediği ölçüldü (25.08.2026). Ayrıştırılan
# sayı bu oranın altına düşerse bölge sayfalarının bir kısmı sessizce
# kaybolmuş demektir; envanteri yarım yazmaktansa hiç yazmamak doğru.
MIN_INDEX_COVERAGE = 0.70

_LEGACY_PROPS_RE = re.compile(r'data-react-props="([^"]+)"')
_INERTIA_PROPS_RE = re.compile(
    r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', re.S
)


class SayfaBicimiDegisti(RuntimeError):
    """Sayfada hiçbir prop bloğu yok — kaynağın biçimi değişmiş."""


def _page_props(text):
    """Sayfanın prop sözlüğünü döndürür. İki biçimi de tanır.

    Bulamazsa BOŞ SÖZLÜK DÖNMEZ, hata fırlatır. Eski davranış tam olarak
    buydu: bot iki hafta boyunca "0 istasyon" deyip başarısız oldu ama
    günlükte sebebi gösteren tek satır yoktu (modül başlığına bakın).
    """
    match = _LEGACY_PROPS_RE.search(text)
    if match:
        # Öznitelik içinde durduğu için HTML kaçışlıdır.
        return json.loads(html.unescape(match.group(1)))

    match = _INERTIA_PROPS_RE.search(text)
    if match:
        # Script gövdesi HAM JSON. html.unescape UYGULANMAZ: veri içindeki
        # düz bir "&amp;" dizisini yanlışlıkla "&" yapardı.
        return json.loads(match.group(1)).get("props") or {}

    raise SayfaBicimiDegisti(
        "Sayfada prop bloğu yok (ne data-react-props özniteliği ne de "
        "<script type=\"application/json\">) — kaynağın biçimi değişmiş."
    )


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
    props = _page_props(_get(LOCATIONS_URL))
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
    props = _page_props(_get(location_page["url"]))
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


_POSTA_KODU = re.compile(r"\b\d{4,6}\b")
_ULKE_KODLARI = {"TR", "TURKIYE", "TURKEY"}
# Uzun il adları önce denenmeli: "KAHRAMANMARAS" içinde "MARAS" yok ama
# "AFYONKARAHISAR" içinde "KARABUK" gibi kısa adların kısmi eşleşmesi
# sıralama olmadan mümkün.
_ILLER_UZUNDAN = tuple(sorted(PROVINCES, key=len, reverse=True))


def _segmentleri_ayikla(value):
    """Adresi anlamlı parçalara böler; posta kodu ve ülke kodunu atar."""
    parcalar = []
    for ham in re.split(r"[\n,]+", value or ""):
        temiz = normalize_city(ham)
        temiz = _POSTA_KODU.sub(" ", temiz)
        temiz = re.sub(r"\s+", " ", temiz).strip(" -/.,")
        if temiz and temiz not in _ULKE_KODLARI:
            parcalar.append(temiz)
    return parcalar


def _ilceyi_temizle(metin):
    metin = re.sub(r"[^A-Z0-9 ]+", " ", metin.strip(" -/"))
    return re.sub(r"\s+", " ", metin).strip()


def _city_district_from_text(value):
    """Serbest metinden (il, ilçe) çıkarır.

    --- NEDEN SONDAN BAŞA VE NEDEN "İLE BİTEN" ------------------------------

    Shell adresleri şu kalıpta: `<cadde>, <posta kodu>, <İLÇE İL>, TR`.
    İl adı SON anlamlı segmentin SONUNDA durur.

    Eski sürüm bunun tersini yapıyordu: adresin TAMAMINI tek parça olarak
    tarayıp en uzun il adını nerede geçerse kabul ediyordu. Türkiye'de
    caddeler komşu illerin adını taşır, dolayısıyla bu kalıcı olarak yanlış
    il üretiyordu — ve üretti:

        'ANKARA ASFALTİ YANYOL 21, 34860, KARTAL İSTANBUL, TR' -> ANKARA
        'SIVAS CAD. 13/B, 66300, AKDAĞMADENİ YOZGAT, TR'       -> SIVAS
        'İZMİR ÇANAKKALE YOLU BLV. 335, 10280, AYVALIK BALIKESİR' -> ÇANAKKALE

    Canlıda 42 Shell istasyonu bu yüzden YANLIŞ İLDE duruyordu (25.08.2026'da
    ölçüldü). Her biri kendi ilinin değil, cadde adındaki ilin fiyatını
    alıyordu. Bağımsız doğrulama: 42'sinin de 15 km içindeki en yakın RAKİP
    marka istasyonunun ili, bu fonksiyonun verdiği ille örtüşüyor — eskisiyle
    örtüşen tek kayıt yok.
    """
    segmentler = _segmentleri_ayikla(value)

    # 1) Bir segment il adıyla BİTİYOR mu? Adresin kanonik kalıbı budur.
    for segment in reversed(segmentler):
        for il in _ILLER_UZUNDAN:
            match = re.search(rf"(^|[\s\-/]){re.escape(il)}$", segment)
            if match:
                return il, _ilceyi_temizle(segment[:match.start()])

    # 2) Kalıp tutmadı. Sondaki segmentlerde geçen il adını kabul et, ama
    #    EN SONDAKİ geçişi al: "İZMİR ... KEMALPAŞA İZMİR" gibi metinlerde
    #    doğru olan ikincisidir.
    for segment in reversed(segmentler):
        en_son = None
        for il in _ILLER_UZUNDAN:
            for match in re.finditer(rf"(^|[\s\-/]){re.escape(il)}($|[\s\-/])", segment):
                if en_son is None or match.start() > en_son[1]:
                    en_son = (il, match.start())
        if en_son:
            return en_son[0], _ilceyi_temizle(segment[:en_son[1]])

    return "", ""


def _parse_station_detail(station):
    props = _page_props(_get(station["url"]))
    location = props.get("location") or {}
    address = location.get("formatted_address") or station.get("list_address") or ""
    city, district = _city_district_from_text(address)

    # Bölge sayfasının adı ikinci kaynak: "MERKEZ ADIYAMAN", "19 MAYIS SAMSUN"
    # gibi zaten "<İLÇE> <İL>" kalıbında ve Shell'in KENDİ dizininden geliyor.
    # Merkez ilçelerde adres yalnızca il adını taşıyor ("..., 02000, ADIYAMAN,
    # TR"); ilçe boş kalırsa fiyat eşleşmesi tutmaz, bu yüzden ilçeyi buradan
    # tamamlıyoruz. İl aynı değilse dokunmuyoruz — bölge adı, istasyonun il
    # sınırının hemen ötesindeki bir bölgeye bağlanmış olabilir.
    grup_il, grup_ilce = _city_district_from_text(station.get("group_name") or "")
    if not city:
        city, district = grup_il, grup_ilce
    elif not district and grup_il == city:
        district = grup_ilce

    location_id_match = re.search(r"/fuel/(\d+)-", station["url"])
    location_id = location.get("location_id") or (
        location_id_match.group(1) if location_id_match else ""
    )
    name = location.get("name") or station.get("list_name")
    return {
        "marka": BRAND,
        "istasyon_adi": name,
        "resmi_unvan": f"{name} {location_id}" if name and location_id else name,
        "il": city,
        "ilce": district,
        "adres": address,
        "enlem": location.get("lat"),
        "boylam": location.get("lng"),
        "veri_kaynagi": SOURCE,
    }


def _load_live_points():
    if supabase is None:
        return []
    points, start = [], 0
    while True:
        page = (
            supabase.table("istasyonlar")
            .select("id,enlem,boylam")
            .eq("marka", BRAND)
            .eq("aktif", True)
            .order("id")
            .range(start, start + 999)
            .execute()
            .data
            or []
        )
        for row in page:
            if row.get("enlem") is not None and row.get("boylam") is not None:
                points.append((float(row["enlem"]), float(row["boylam"])))
        if len(page) < 1000:
            break
        start += 1000
    return points


def _ham_kayitlari_topla():
    """Kaynaktan ham istasyon sözlüklerini toplar. Süzgeç uygulanmaz."""
    location_pages = _locations_index()
    expected = sum(int(page["count"] or 0) for page in location_pages)
    print(f"[INFO] Shell bölge sayfası: {len(location_pages)}, "
          f"listelenen istasyon: {expected}")

    stations_by_url = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(_station_links, page) for page in location_pages]
        for future in as_completed(futures):
            try:
                for station in future.result():
                    stations_by_url[station["url"]] = station
            except Exception as exc:
                print(f"[WARN] Shell bölge sayfası atlandı: {exc}")

    print(f"[INFO] Shell istasyon detay bağlantısı: {len(stations_by_url)}")

    # Dizin 1.289 istasyon vaat ediyor ama bağlantıların büyük kısmı
    # toplanamadıysa envanteri YARIM yazmak, olmayan istasyonları silmekten
    # beter: `aktif` kalırlar ama koordinatları güncellenmez ve bir daha
    # hangi koşunun eksik olduğu anlaşılmaz. Yarım veriyle devam etme.
    if expected and len(stations_by_url) < expected * MIN_INDEX_COVERAGE:
        raise SayfaBicimiDegisti(
            f"Bölge sayfalarından yalnızca {len(stations_by_url)}/{expected} "
            f"istasyon bağlantısı toplanabildi (eşik %"
            f"{MIN_INDEX_COVERAGE * 100:.0f}) — kaynak erişilemez durumda."
        )

    scraped = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(_parse_station_detail, station)
            for station in stations_by_url.values()
        ]
        for index, future in enumerate(as_completed(futures), start=1):
            try:
                scraped.append(future.result())
            except Exception as exc:
                print(f"[WARN] Shell istasyon detayı atlandı: {exc}")
            if index % 200 == 0:
                print(f"[INFO] Shell detay ayrıştırıldı: {index}/{len(futures)}")
    return scraped


def scrape_data():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Shell station bot started.")
    try:
        ham = _ham_kayitlari_topla()
    except Exception as exc:
        print(f"[WARN] Shell station scrape failed: {exc}")
        return [], 0

    if not ham:
        print("[WARN] Kaynaktan hiçbir istasyon çıkarılamadı — biçim değişmiş "
              "olabilir. Hiçbir şey yazılmıyor.")
        return [], 0

    live_points = _load_live_points()
    near, far = yakinlik_indeksleri(live_points, BRAND)

    scraped, karantina, bozuk_il = [], [], []
    gorulen = set()

    for row in ham:
        latitude, longitude = row.get("enlem"), row.get("boylam")
        if not latitude or not longitude:
            continue
        latitude, longitude = float(latitude), float(longitude)

        if not gecerli_konum(row.get("il"), row.get("ilce")):
            bozuk_il.append((row.get("il"), row.get("ilce"), row.get("istasyon_adi")))
            continue

        # `unique_isim_ilce_adres` kısıtı aynı dörtlüyü reddeder ve TÜM partiyi
        # düşürür. Bot kendi içinde temizler (po_station_bot ile aynı kural).
        kimlik = (
            str(row.get("istasyon_adi") or "").strip().casefold(),
            str(row.get("il") or "").strip().casefold(),
            str(row.get("ilce") or "").strip().casefold(),
            str(row.get("adres") or "").strip().casefold(),
        )
        if kimlik in gorulen:
            continue
        gorulen.add(kimlik)

        if karantinada_mi(near, far, BRAND, latitude, longitude):
            karantina.append((
                en_yakin_metre(live_points, latitude, longitude),
                row.get("istasyon_adi"),
                row.get("il"),
            ))
            continue

        scraped.append(row)

    rapor_yaz(bozuk_il, karantina)
    return scraped, len(karantina) + len(bozuk_il)


if __name__ == "__main__":
    start_time = datetime.now()
    data, elenen = scrape_data()
    print(f"[INFO] Shell official station rows fetched: {len(data)} (elenen: {elenen})")
    summary = save_station_inventory_to_supabase(data, default_brand=BRAND)
    print(f"[OK] Shell station bot finished in {(datetime.now() - start_time).total_seconds():.1f}s.")
    raise SystemExit(finish_bot_run("shell_station_bot.py", scraped=len(data), summary=summary))
