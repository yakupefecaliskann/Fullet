"""Aytemiz resmi istasyon envanteri botu (F4-4).

Kaynak: Aytemiz'in "en yakin istasyon" haritasi. PO'daki gibi API yok; veri
sayfaya gomulu bir JS dizisinde duruyor:

    GET https://www.aytemiz.com.tr/haritalar/en-yakin-aytemiz   (~710 KB)
    ...<script>var markers=[{...},{...}]</script>...

Kayit bicimi (Unicode kacisli):
    {"City":"Yozgat","County":"Akdagmadeni","Title":"Akdag Bora Petrol ...",
     "Address":"Ibrahim Aga Mah. ... Akdagmadeni Yozgat",
     "Lat":"39.659545","Lon":"35.883444","Phone":"3543143636",
     "ayt":"VAR","gaz":"YOK","market":"YOK", ...}

Dikkat: boylam alani `Lon` (PO'da `Longitude`, Opet'te `longitude`).
Koordinatlar STRING olarak geliyor, sayiya cevrilmeli.

Olculdu (4 Agustos 2026): 876 istasyon. Bizde 35 kayit vardi.

Guvenlik suzgecleri `station_inventory_common`'da; gerekcesi orada yazili.
"""
from __future__ import annotations

import json
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

PAGE_URL = "https://www.aytemiz.com.tr/haritalar/en-yakin-aytemiz"
SOURCE = "aytemiz.com.tr/haritalar/en-yakin-aytemiz"
BRAND = "Aytemiz"
HEADERS = {"User-Agent": "Mozilla/5.0 (Fullet official station inventory)"}
DIZI_BASI = "var markers="


def _dizi_sonu(metin: str, start: int) -> int:
    """start'taki '[' ile eslesen ']' konumu; bulunamazsa -1.

    Adres ve unvan alanlarinda koseli parantez gecebildigi icin string
    icindeyken parantez sayilmaz.
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
            elif ch in "[{":
                derinlik += 1
            elif ch in "]}":
                derinlik -= 1
                if derinlik == 0:
                    return i
        i += 1
    return -1


def _sayfadan_istasyonlari_cikar(html: str) -> list[dict]:
    """`var markers=[...]` dizisini cozer."""
    konum = html.find(DIZI_BASI)
    if konum < 0:
        return []
    bas = html.find("[", konum)
    if bas < 0:
        return []
    son = _dizi_sonu(html, bas)
    if son < 0:
        return []
    try:
        kayitlar = json.loads(html[bas:son + 1])
    except json.JSONDecodeError as exc:
        print(f"[WARN] markers dizisi cozulemedi: {exc}")
        return []
    return kayitlar if isinstance(kayitlar, list) else []


def _koordinat(deger):
    """Aytemiz koordinatlari string gonderiyor ('39.659545')."""
    if deger in (None, ""):
        return None
    try:
        return float(str(deger).strip().replace(",", "."))
    except ValueError:
        return None


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
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Aytemiz station bot started.")
    try:
        response = HTTP.get(PAGE_URL, headers=HEADERS, timeout=(5, 60))
        response.raise_for_status()
        rows = _sayfadan_istasyonlari_cikar(response.text)
    except Exception as exc:
        print(f"[WARN] Aytemiz station scrape failed: {exc}")
        return [], 0

    if not rows:
        print("[WARN] Sayfadan hicbir istasyon cikarilamadi — bicim degismis "
              "olabilir. Hicbir sey yazilmiyor.")
        return [], 0

    print(f"[INFO] Sayfadan {len(rows)} istasyon cikarildi.")

    live_points = _load_live_points()
    near, far = yakinlik_indeksleri(live_points, BRAND)

    scraped, karantina, bozuk_il = [], [], []
    gorulen = set()

    for row in rows:
        latitude = _koordinat(row.get("Lat"))
        longitude = _koordinat(row.get("Lon"))
        if latitude is None or longitude is None:
            continue

        il_ham, ilce_ham = row.get("City"), row.get("County")
        if not gecerli_konum(il_ham, ilce_ham):
            bozuk_il.append((il_ham, ilce_ham, row.get("Title")))
            continue

        kimlik = (
            str(row.get("Title") or "").strip().casefold(),
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
                row.get("Title"),
                il_ham,
            ))
            continue

        scraped.append({
            "marka": BRAND,
            "istasyon_adi": row.get("Title"),
            "resmi_unvan": row.get("Title"),
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
    print(f"[INFO] Aytemiz official station rows fetched: {len(data)} "
          f"(elenen: {elenen})")
    summary = save_station_inventory_to_supabase(data, default_brand=BRAND)
    print(f"[OK] Aytemiz station bot finished in "
          f"{(datetime.now() - start_time).total_seconds():.1f}s.")
    raise SystemExit(finish_bot_run("aytemiz_station_bot.py", scraped=len(data), summary=summary))
