"""Petrol Ofisi resmi istasyon envanteri botu (F4-3).

Kaynak: PO'nun istasyon bulucu sayfasi. API arayip bulamadik — veri zaten
sayfanin icinde, JS'e gomulu JSON olarak duruyor:

    GET https://www.petrolofisi.com.tr/istasyon-nerede   (~3,1 MB)

Sayfa il il bolunmus dizilerde ayni istasyonu birden fazla kez tasiyor
(7.869 nesne, 2.623 benzersiz Id). Bu yuzden nesneler tek tek cikarilip
`Id` uzerinden tekillestirilir.

Kayit bicimi:
    {"Id":989,"StationName":"ADASARHANLI",
     "Address":"ADASARHANLI KOYU, MERIC, Edirne",
     "CityName":"Edirne","DistrictName":"MERIC",
     "Latitude":41.083913,"Longitude":26.355788, ...}

Olculdu (4 Agustos 2026): 2.623 benzersiz istasyon, 81 il, isim/adres/il/
ilce bos 0, koordinatsiz 0, gecersiz il 0, Turkiye disi 0.

--- NEDEN BU MARKA EN BUYUK LOKMA ---------------------------------------

Petrol Ofisi BP Turkiye'yi devraldi (770 istasyon) ve marka donusumu
1 Kasim 2026'da tamamlaniyor. PO boylece ~2.700 istasyona cikti. Bizde
bugune kadar yalnizca 80 PO kaydi vardi — aktif envanterin %3'u.

Guvenlik suzgecleri `station_inventory_common`'da; gerekcesi orada yazili.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime

from http_utils import HTTP

from db_utils import finish_bot_run, save_station_inventory_to_supabase, supabase
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

PAGE_URL = "https://www.petrolofisi.com.tr/istasyon-nerede"
SOURCE = "petrolofisi.com.tr/istasyon-nerede"
BRAND = "Petrol Ofisi"
HEADERS = {"User-Agent": "Mozilla/5.0 (Fullet official station inventory)"}

_NESNE_BASI = re.compile(r'\{"Id":\d+,"StationName"')


def _dengeli_nesne_sonu(metin: str, start: int) -> int:
    """start'taki '{' ile eslesen '}' konumu; bulunamazsa -1.

    Duz regex yetmez: adres alanlarinda sussu parantez ve kacisli tirnak
    olabiliyor. String icindeyken parantez saymayi biraktigimiz icin
    "NO:1{" gibi bir adres diziyi bolmez.
    """
    derinlik, i, in_str, esc = 0, start, False, False
    while i < len(metin):
        ch = metin[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                derinlik += 1
            elif ch == "}":
                derinlik -= 1
                if derinlik == 0:
                    return i
        i += 1
    return -1


def _sayfadan_istasyonlari_cikar(html: str) -> list[dict]:
    """Gomulu JSON nesnelerini cikarir ve Id uzerinden tekillestirir."""
    benzersiz: dict[object, dict] = {}
    bozuk = 0
    for match in _NESNE_BASI.finditer(html):
        son = _dengeli_nesne_sonu(html, match.start())
        if son < 0:
            bozuk += 1
            continue
        try:
            kayit = json.loads(html[match.start():son + 1])
        except json.JSONDecodeError:
            bozuk += 1
            continue
        if kayit.get("Id") is not None:
            benzersiz[kayit["Id"]] = kayit
    if bozuk:
        print(f"[WARN] {bozuk} nesne cozulemedi (sayfa bicimi degismis olabilir).")
    return list(benzersiz.values())


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


def scrape_data():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Petrol Ofisi station bot started.")
    try:
        response = HTTP.get(PAGE_URL, headers=HEADERS, timeout=(5, 60))
        response.raise_for_status()
        rows = _sayfadan_istasyonlari_cikar(response.text)
    except Exception as exc:
        print(f"[WARN] Petrol Ofisi station scrape failed: {exc}")
        return [], 0

    if not rows:
        print("[WARN] Sayfadan hicbir istasyon cikarilamadi — bicim degismis "
              "olabilir. Hicbir sey yazilmiyor.")
        return [], 0

    print(f"[INFO] Sayfadan {len(rows)} benzersiz istasyon cikarildi.")

    live_points = _load_live_points()
    near, far = yakinlik_indeksleri(live_points, BRAND)

    scraped, karantina, bozuk_il = [], [], []
    gorulen = set()

    for row in rows:
        latitude, longitude = row.get("Latitude"), row.get("Longitude")
        if not latitude or not longitude:
            continue
        latitude, longitude = float(latitude), float(longitude)

        il_ham, ilce_ham = row.get("CityName"), row.get("DistrictName")
        if not gecerli_konum(il_ham, ilce_ham):
            bozuk_il.append((il_ham, ilce_ham, row.get("StationName")))
            continue

        # `unique_isim_ilce_adres` kisiti ayni dortluyu reddeder ve TUM
        # partiyi dusurur (Opet'te bir kez oldu). Bot kendi icinde temizler.
        kimlik = (
            str(row.get("StationName") or "").strip().casefold(),
            str(il_ham or "").strip().casefold(),
            str(ilce_ham or "").strip().casefold(),
            str(row.get("Address") or "").strip().casefold(),
        )
        if kimlik in gorulen:
            continue
        gorulen.add(kimlik)

        if karantinada_mi(near, far, BRAND, latitude, longitude):
            karantina.append((
                en_yakin_metre(live_points, latitude, longitude),
                row.get("StationName"),
                il_ham,
            ))
            continue

        scraped.append({
            "marka": BRAND,
            "istasyon_adi": row.get("StationName"),
            "resmi_unvan": row.get("StationName"),
            "il": il_ham,
            "ilce": ilce_ham,
            "adres": row.get("Address"),
            "enlem": latitude,
            "boylam": longitude,
            "veri_kaynagi": SOURCE,
        })

    rapor_yaz(bozuk_il, karantina)
    return scraped, len(karantina) + len(bozuk_il)


if __name__ == "__main__":
    start_time = datetime.now()
    data, elenen = scrape_data()
    print(f"[INFO] Petrol Ofisi official station rows fetched: {len(data)} "
          f"(elenen: {elenen})")
    summary = save_station_inventory_to_supabase(data, default_brand=BRAND)
    print(f"[OK] Petrol Ofisi station bot finished in "
          f"{(datetime.now() - start_time).total_seconds():.1f}s.")
    raise SystemExit(finish_bot_run("po_station_bot.py", scraped=len(data), summary=summary))
