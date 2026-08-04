"""F4-0 KAPISI — Opet envanteri akıtmadan önce kopya riskini ölç.

Bu betik HİÇBİR ŞEY YAZMAZ. Sadece okur ve rapor eder.

Neden var: 3 Ağustos'ta 107 kopya birleştirildi ve kopya hatası bu projede iki
kez geri geldi. 1.246 kaydı ölçmeden akıtmak fazı geri alınamaz hale getirir.

--- İKİ AŞAMALI EŞLEŞTİRME (4 Ağustos 2026 kararı) --------------------------

İlk ölçüm %75,9 ile kapıda kaldı. Teşhis: eşleşmeyen 121 kaydın 27'si aslında
AYNI istasyondu, sadece eski kaydın koordinatı kabaydı (48-211 m sapma).

75 m yarıçapı DEĞİŞTİRİLMEDİ. O sınır bilinçli seçilmiş: `test_cleanup_
regressions.ProximityIdentityTest` "75-150 m bandı KASTEN birleştirilmez —
'YAĞLI BATI'/'YAĞLI DOĞU' gibi yol ayrımının iki yanındaki AYRI istasyonlar
oradadır" diyor. Yarıçapı büyütmek o ayrımı yok ederdi.

Onun yerine ikinci bir tur eklendi:

    Tur 1: 75 m  — mevcut katı kural, dokunulmadı
    Tur 2: aynı marka + il + ilçe içinde 250 m, AMA yalnızca 1-e-1 ise

1-e-1 şartı YAĞLI BATI/DOĞU sorununu çözer: yol ayrımının iki yanındaki iki
istasyon da 250 m içindeyse aday sayısı 2 olur, hangisinin hangisi olduğu
belirsizdir ve eşleştirme YAPILMAZ. Belirsizlik kopya üretmekten iyidir.
"""
from __future__ import annotations

import sys
from collections import defaultdict

import requests

from db_utils import supabase
from matching import StationProximityIndex, _haversine
from normalization import normalize_city, normalize_province

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

API = "https://api.opet.com.tr/api/stations/v2"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Fullet station inventory)",
    "Accept": "application/json",
    "Origin": "https://www.opet.com.tr",
    "Referer": "https://www.opet.com.tr/benzin-istasyonu-arama",
}

TUR2_YARICAP_KM = 0.250
KAPI_ESIGI = 90.0


def fetch_api_stations():
    response = requests.post(API, headers=HEADERS, json={}, timeout=60)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise SystemExit(f"Beklenmeyen govde tipi: {type(data)}")
    return data


def load_live_opet():
    rows, start = [], 0
    while True:
        page = (
            supabase.table("istasyonlar")
            .select("id,isim,il,ilce,enlem,boylam,aktif,adres")
            .eq("marka", "Opet")
            .order("id")
            .range(start, start + 999)
            .execute()
            .data
            or []
        )
        rows.extend(page)
        if len(page) < 1000:
            break
        start += 1000
    return rows


def _bolge_anahtari(il, ilce):
    return (normalize_province(il) or "", normalize_city(ilce) or "")


def main():
    print("=== F4-0 KAPISI: Opet envanteri kopya riski olcumu ===\n")

    api_rows = fetch_api_stations()
    print(f"[API]   {len(api_rows)} istasyon dondu")

    live_rows = load_live_opet()
    live_active = [r for r in live_rows if r.get("aktif")]
    print(f"[CANLI] {len(live_rows)} Opet kaydi ({len(live_active)} aktif)\n")

    # --- API tarafinin veri kalitesi ---
    print("--- API veri kalitesi ---")
    for etiket, kosul in (
        ("koordinatsiz", lambda r: not r.get("latitude") or not r.get("longitude")),
        ("isimsiz", lambda r: not (r.get("name") or "").strip()),
        ("adressiz", lambda r: not (r.get("address") or "").strip()),
        ("ilsiz", lambda r: not (r.get("province") or "").strip()),
    ):
        print(f"  {etiket:13}: {sum(1 for r in api_rows if kosul(r))}")

    # --- Tur 1 indeksi: 75 m (mevcut kati kural) ---
    tur1 = StationProximityIndex()
    api_ici_kopya = 0
    api_gecerli = []
    for row in api_rows:
        lat, lon = row.get("latitude"), row.get("longitude")
        if not lat or not lon:
            continue
        lat, lon = float(lat), float(lon)
        if tur1.find("Opet", lat, lon):
            api_ici_kopya += 1
            continue
        tur1.add("Opet", lat, lon, row["id"])
        api_gecerli.append((row["id"], lat, lon, row.get("province"), row.get("district")))
    print(f"  API ici kopya: {api_ici_kopya}\n")

    # API kayitlarini bolgeye gore grupla (Tur 2 icin)
    api_bolge = defaultdict(list)
    for sid, lat, lon, il, ilce in api_gecerli:
        api_bolge[_bolge_anahtari(il, ilce)].append((sid, lat, lon))

    # --- Eslestirme ---
    tur1_eslesen, tur2_eslesen, eslesmeyen = 0, 0, []
    tur2_belirsiz = 0
    kullanilmis_api = set()

    for row in live_active:
        lat, lon = row.get("enlem"), row.get("boylam")
        if lat is None or lon is None:
            eslesmeyen.append(row)
            continue
        lat, lon = float(lat), float(lon)

        # Tur 1: 75 m
        hit = tur1.find("Opet", lat, lon)
        if hit:
            tur1_eslesen += 1
            kullanilmis_api.add(hit)
            continue

        # Tur 2: ayni il+ilce icinde 250 m, YALNIZCA 1-e-1
        adaylar = [
            (sid, _haversine(lat, lon, a, b))
            for sid, a, b in api_bolge.get(_bolge_anahtari(row.get("il"), row.get("ilce")), ())
            if _haversine(lat, lon, a, b) <= TUR2_YARICAP_KM
        ]
        adaylar = [(sid, d) for sid, d in adaylar if sid not in kullanilmis_api]

        if len(adaylar) == 1:
            tur2_eslesen += 1
            kullanilmis_api.add(adaylar[0][0])
        else:
            if len(adaylar) > 1:
                tur2_belirsiz += 1
            eslesmeyen.append(row)

    toplam = len(live_active)
    eslesen = tur1_eslesen + tur2_eslesen
    oran = (eslesen / toplam * 100) if toplam else 0.0

    print("--- KAPI OLCUMU: canli kayitlar API'de bulunuyor mu? ---")
    print(f"  Tur 1 (75 m)            : {tur1_eslesen}")
    print(f"  Tur 2 (250 m, 1-e-1)    : {tur2_eslesen}")
    print(f"  Tur 2 belirsiz (atlandi): {tur2_belirsiz}")
    print(f"  TOPLAM eslesen          : {eslesen}/{toplam}  (%{oran:.1f})")
    print(f"  eslesmeyen              : {len(eslesmeyen)}")

    if eslesmeyen:
        print("\n  Eslesmeyen ilk 8 (F4-2 artik adaylari):")
        for row in eslesmeyen[:8]:
            print(f"    - {row.get('isim')!r} {row.get('il')}/{row.get('ilce')}")

    yeni = len(api_gecerli) - eslesen
    print(f"\n--- Tahmini net kazanc: +{yeni} yeni istasyon "
          f"({toplam} -> ~{toplam + yeni}) ---")

    print("\n=== KAPI KARARI ===")
    if oran >= KAPI_ESIGI:
        print(f"  GECTI (%{oran:.1f} >= %{KAPI_ESIGI:.0f}) — F4-1 akitmasi guvenli.")
        return 0
    print(f"  KALDI (%{oran:.1f} < %{KAPI_ESIGI:.0f}) — AKITMA.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
