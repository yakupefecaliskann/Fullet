"""Opet resmi istasyon envanteri botu (F4-1).

Kaynak: Opet'in kendi istasyon bulucu API'si.
  POST https://api.opet.com.tr/api/stations/v2   -> 1.246 istasyon
  (GET 401 doner; endpoint FindStation.js web component'inden cikarildi)

Donen kayit tam donanimli: ticari unvan, tam adres, il, ilce, koordinat.
Olculdu (4 Agustos 2026): koordinatsiz 0, isimsiz 0, adressiz 0, ilsiz 0.

--- KARANTINA KURALI — bu botun en onemli kismi -----------------------------

Envanter yazma yolu (`_bulk_write_station_inventory`) 75 m yaricapli
`StationProximityIndex` kullanir: 75 m icinde eslesen kaydi GUNCELLER,
eslesmeyeni EKLER. Bu ikili karar bizim icin yeterli degil.

F4-0 olcumu (canli, 4 Agustos 2026) sunu gosterdi:

    <75 m      387 kayit  -> mevcut kayitla ayni, guncellenecek
    75-250 m    13 kayit  -> SUPHELI
    250m-1km    61 kayit  -> SUPHELI
    >1 km      785 kayit  -> kesinlikle yeni istasyon

Ortadaki 74 kayit belirsiz. Ornekler acikca ayni istasyonu gosteriyor:

    82 m   API 'PURLU OTOMOTIV...'   <-> canli 'Opet Isparta Merkez'
    107 m  API 'MOBIPA MOBILYA...'   <-> canli 'Opet Inegol'

Eski kayitlarin koordinati kaba (ilce merkezine yuvarlanmis); API'ninki kesin.
Bunlari korlemesine eklemek 74 kopya uretirdi. 75 m yaricapini buyutmek ise
`ProximityIdentityTest`'in korudugu ayrimi bozardi: "75-150 m bandi KASTEN
birlestirilmez — 'YAGLI BATI'/'YAGLI DOGU' gibi yol ayriminin iki yanindaki
AYRI istasyonlar oradadir."

Cozum: supheli bandi HIC GONDERME. Bot yalnizca iki uc grubu yazar:
kesin ayni (<75 m, guncellenir) ve kesin farkli (>1 km, eklenir). Aradaki
belirsizlik karantinada raporlanir ve F4-2'de elle karara baglanir.
Belirsizlikte kopya uretmektense istasyon eklememek yeglenir.
"""
from __future__ import annotations

import sys
from datetime import datetime

from http_utils import HTTP

from config import ISTANBUL_REGION_DISTRICTS
from db_utils import finish_bot_run, save_station_inventory_to_supabase, supabase
from matching import StationProximityIndex, _haversine
from normalization import PROVINCES, normalize_city, normalize_province

# ANADOLU + AVRUPA listelerinin birlesimi: fiyat yolunun tanidigi tum
# Istanbul ilceleri. Tek dogruluk kaynagi config.ISTANBUL_REGION_DISTRICTS.
_ISTANBUL_ILCELERI = {
    ilce for bolge in ISTANBUL_REGION_DISTRICTS.values() for ilce in bolge
}

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

API_URL = "https://api.opet.com.tr/api/stations/v2"
SOURCE = "api.opet.com.tr/api/stations/v2"
BRAND = "Opet"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Fullet official station inventory)",
    "Accept": "application/json",
    "Origin": "https://www.opet.com.tr",
    "Referer": "https://www.opet.com.tr/benzin-istasyonu-arama",
}

# Karantina bandi. Alt sinir envanter yolunun yaricapiyla AYNI olmali
# (matching.STATION_MATCH_RADIUS_METERS = 75 m), yoksa arada yazilan bir
# bosluk kalir ve supheli kayit sessizce eklenir.
KARANTINA_ALT_KM = 0.075
KARANTINA_UST_KM = 1.0


def _fetch_stations():
    response = HTTP.post(API_URL, headers=HEADERS, json={}, timeout=(5, 60))
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list):
        raise ValueError(f"Beklenmeyen govde tipi: {type(rows).__name__}")
    return rows


def _load_live_points():
    """Mevcut Opet kayitlarinin (enlem, boylam, isim) listesi."""
    if supabase is None:
        return []
    points, start = [], 0
    while True:
        page = (
            supabase.table("istasyonlar")
            .select("id,isim,enlem,boylam")
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
                points.append((float(row["enlem"]), float(row["boylam"]), row.get("isim")))
        if len(page) < 1000:
            break
        start += 1000
    return points


def scrape_data():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Opet station bot started.")
    try:
        rows = _fetch_stations()
    except Exception as exc:
        print(f"[WARN] Opet station scrape failed: {exc}")
        return [], 0

    live_points = _load_live_points()
    # Iki indeks: 75 m "kesin ayni", 1 km "supheli yakinlik". Hucre boyutu
    # 0,01 derece (~1,1 km) ve komsu hucreler de tarandigi icin 1 km yaricap
    # bu indekste guvenle calisir.
    near_index = StationProximityIndex(radius_meters=KARANTINA_ALT_KM * 1000)
    far_index = StationProximityIndex(radius_meters=KARANTINA_UST_KM * 1000)
    for lat, lon, name in live_points:
        near_index.add(BRAND, lat, lon, name)
        far_index.add(BRAND, lat, lon, name)

    scraped, karantina, bozuk_il = [], [], []
    # API kendi icinde de tam kopya barindiriyor: ayni (isim, il, ilce, adres)
    # dortlusu 1.246 kayitta bir kez tekrar ediyor. Veritabanindaki
    # `unique_isim_ilce_adres` kisiti bunu reddeder ve TUM parti yazilmaz
    # (canlida bir kez oldu: 1.172 kaydin hicbiri yazilamadi). Botun kendisi
    # temizler ki tek bozuk kayit butun akitmayi dusurmesin.
    gorulen_kimlikler = set()
    for row in rows:
        latitude, longitude = row.get("latitude"), row.get("longitude")
        if not latitude or not longitude:
            continue
        latitude, longitude = float(latitude), float(longitude)

        kimlik = (
            str(row.get("name") or "").strip().casefold(),
            str(row.get("province") or "").strip().casefold(),
            str(row.get("district") or "").strip().casefold(),
            str(row.get("address") or "").strip().casefold(),
        )
        if kimlik in gorulen_kimlikler:
            continue
        gorulen_kimlikler.add(kimlik)

        # IL DOGRULAMASI. Kaynagin `province` alani her zaman il degil: canlida
        # bir kayit il alaninda CADDE ADI tasiyordu ("TAYAKADIN YASSIOREN
        # CADDE", ilcesi ARNAVUTKOY). Boyle bir kayit hicbir il eslesmesine
        # giremez, dolayisiyla fiyat da alamaz ve kalici olarak `hidden`
        # kalir — yani sessiz bir cop kayit olur. 81 il listesi tek dogruluk
        # kaynagidir (normalization.PROVINCES).
        il = normalize_province(row.get("province"))
        if il not in PROVINCES:
            bozuk_il.append((row.get("province"), row.get("district"), row.get("name")))
            continue

        # ISTANBUL'un ozel durumu: fiyat yolu Istanbul'u ANADOLU/AVRUPA
        # bolgelerine ayirir (`ISTANBUL_REGION_DISTRICTS`). Bu iki listenin
        # disinda kalan bir ilce -- canlida "MERKEZ" goruldu -- hicbir bolgeye
        # giremez; `_reset_split_region_targets` onu pasiflestirir ve bir daha
        # aktiflestirmez. Il gecerli oldugu icin yukaridaki kontrol yakalamaz.
        if il == "ISTANBUL" and normalize_city(row.get("district")) not in _ISTANBUL_ILCELERI:
            bozuk_il.append((row.get("province"), row.get("district"), row.get("name")))
            continue

        # <75 m ise mevcut kayitla ayni sayilir -> gonder, yazma yolu gunceller.
        # Degilse ama 1 km icinde bir kayit varsa karar belirsizdir -> GONDERME.
        if not near_index.find(BRAND, latitude, longitude):
            komsu = far_index.find(BRAND, latitude, longitude)
            if komsu is not None:
                mesafe_m = min(
                    _haversine(latitude, longitude, lat, lon) * 1000
                    for lat, lon, _ in live_points
                )
                karantina.append((mesafe_m, row.get("name", ""), row.get("province", "")))
                continue

        scraped.append({
            "marka": BRAND,
            "istasyon_adi": row.get("name"),
            "resmi_unvan": row.get("name"),
            "il": row.get("province"),
            "ilce": row.get("district"),
            "adres": row.get("address"),
            "enlem": latitude,
            "boylam": longitude,
            "veri_kaynagi": SOURCE,
        })

    if bozuk_il:
        print(f"[BOZUK IL] {len(bozuk_il)} kayit YAZILMADI (il alani 81 il "
              f"listesinde degil; fiyat eslesmesine giremez, cop kayit olurdu):")
        for province, district, name in bozuk_il[:5]:
            print(f"           il={str(province)[:32]!r} ilce={str(district)[:20]!r} "
                  f"{str(name)[:34]!r}")

    if karantina:
        print(f"[KARANTINA] {len(karantina)} supheli kayit YAZILMADI "
              f"({KARANTINA_ALT_KM * 1000:.0f}-{KARANTINA_UST_KM * 1000:.0f} m bandinda "
              f"mevcut bir kayda yakin). F4-2'de elle karara baglanacak.")
        for distance, name, province in sorted(karantina)[:10]:
            print(f"             {distance:6.0f} m  {str(name)[:44]!r} ({province})")
        if len(karantina) > 10:
            print(f"             ... ve {len(karantina) - 10} kayit daha")

    return scraped, len(karantina) + len(bozuk_il)


if __name__ == "__main__":
    start_time = datetime.now()
    data, quarantined = scrape_data()
    print(f"[INFO] Opet official station rows fetched: {len(data)} "
          f"(karantina: {quarantined})")
    summary = save_station_inventory_to_supabase(data, default_brand=BRAND)
    print(f"[OK] Opet station bot finished in "
          f"{(datetime.now() - start_time).total_seconds():.1f}s.")
    raise SystemExit(finish_bot_run("opet_station_bot.py", scraped=len(data), summary=summary))
