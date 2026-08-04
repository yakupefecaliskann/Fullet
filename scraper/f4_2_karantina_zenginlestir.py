"""F4-2: karantinadaki kayitlari ZENGINLESTIR (yeni istasyon EKLEME).

F4-1, 75 m - 1 km bandinda mevcut bir kayda yakin olan 74 API kaydini
kasten yazmadi. Olcum bunlarin ayni istasyon oldugunu gosteriyor:

     82 m  API 'PURLU OTOMOTIV...'  <->  canli 'Opet Isparta Merkez'
    107 m  API 'MOBIPA MOBILYA...'  <->  canli 'Opet Inegol'

Eski kayitlarin koordinati kaba (ilce merkezine yuvarlanmis), ismi jenerik
("Opet Inegol") ve adresi hic yok. API'ninki kesin: gercek ticari unvan,
tam adres, dogru koordinat.

KARAR (kullanici, 4 Agustos 2026): ayri istasyon olarak EKLEME — haritada
kopya coplugu yaratir. Eski kaydi API verisiyle GUNCELLE.

--- 1-e-1 GUVENLIK KURALI --------------------------------------------------

Bir API kaydi ile bir canli kaydi yalnizca ikisi de birbirinin TEK adayiysa
eslestirilir. Iki yonlu kontrol:

    * API kaydinin bantta tek canli komsusu olmali
    * O canli kaydin da bantta tek API komsusu olmali

Aksi halde hangisinin hangisi oldugu belirsizdir ve yanlis istasyonun adresi
yazilir. Belirsiz kalanlar RAPORLANIR, dokunulmaz. Bu, "YAGLI BATI/DOGU"
vakasinin zenginlestirme tarafindaki karsiligidir.

Koordinat da guncellenir: boylece bir sonraki bot kosusunda kayit API ile
<75 m icinde eslesir ve karantina bandindan kalici olarak cikar.

Kullanim:
    python f4_2_karantina_zenginlestir.py           # dry-run, hicbir sey yazmaz
    python f4_2_karantina_zenginlestir.py --uygula   # canliya yazar
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timezone

import requests

from config import ISTANBUL_REGION_DISTRICTS
from db_utils import supabase
from matching import StationProximityIndex, _fuzzy_match_name, _haversine
from normalization import (
    PROVINCES,
    clean_text,
    normalize_city,
    normalize_province,
)

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

ALT_KM = 0.075
UST_KM = 1.0

_ISTANBUL_ILCELERI = {
    ilce for bolge in ISTANBUL_REGION_DISTRICTS.values() for ilce in bolge
}


def _jenerik_isim(isim: str) -> bool:
    """Eski kayit kimliksiz mi?

    'Opet Inegol', 'Opet Bitlis Merkez' gibi isimler istasyonun kendi ticari
    unvani degil, marka + yer etiketidir. Bu kayitlarda API verisi kesin
    iyilestirmedir: kaybedilecek kimlik yoktur.
    """
    temiz = (isim or "").strip().casefold()
    if not temiz:
        return True
    return temiz.startswith("opet")


def _ayni_isletme(eski_isim: str, api_isim: str) -> bool:
    """Iki ticari unvan ayni isletmeyi mi gosteriyor?

    Neden gerekli: 1-e-1 yakinlik kurali tek basina yetmiyor. Canli olcumde
    bant icinde su ciftler cikti ve ikisi de FARKLI mahallede:

        'PARMAKSIZLAR PETROL' (EFELER MAH. NO:6)
            <-> 'OZTURKLER ENERJI' (CUMHURIYET MAH. NO:42/1)   159 m
        'GOKMENOGLU MADENCILIK' (KALEKAPU MAH.)
            <-> 'GKM AKARYAKIT' (ERENLER MAH.)                  180 m

    Bunlar buyuk olasilikla AYRI istasyonlar. Ustune yazmak eski kaydin
    kimligini yok eder ve iki istasyonu tek kayda ezer — kopya eklemekten
    daha kotu, cunku geri alinamaz.
    """
    return bool(_fuzzy_match_name(eski_isim or "", api_isim or ""))


def _gecerli_konum(row):
    il = normalize_province(row.get("province"))
    if il not in PROVINCES:
        return False
    if il == "ISTANBUL" and normalize_city(row.get("district")) not in _ISTANBUL_ILCELERI:
        return False
    return True


def main(uygula: bool) -> int:
    api_rows = requests.post(API_URL, headers=HEADERS, json={}, timeout=60).json()

    live, start = [], 0
    while True:
        page = (
            supabase.table("istasyonlar")
            .select("id,isim,il,ilce,adres,enlem,boylam")
            .eq("marka", BRAND).eq("aktif", True)
            .order("id").range(start, start + 999).execute().data or []
        )
        live.extend(page)
        if len(page) < 1000:
            break
        start += 1000

    live_pts = [
        (r, float(r["enlem"]), float(r["boylam"]))
        for r in live
        if r.get("enlem") is not None and r.get("boylam") is not None
    ]

    near = StationProximityIndex(radius_meters=ALT_KM * 1000)
    for _, lat, lon in live_pts:
        near.add(BRAND, lat, lon, "x")

    # Bant icindeki her (API kaydi -> canli kayit) ciftini topla.
    api_komsulari = {}
    canli_komsulari = defaultdict(list)

    for row in api_rows:
        lat, lon = row.get("latitude"), row.get("longitude")
        if not lat or not lon or not _gecerli_konum(row):
            continue
        lat, lon = float(lat), float(lon)
        if near.find(BRAND, lat, lon):
            continue  # zaten <75 m, F4-1 bunu yazdi

        komsular = [
            (r["id"], _haversine(lat, lon, a, b) * 1000)
            for r, a, b in live_pts
            if _haversine(lat, lon, a, b) <= UST_KM
        ]
        if not komsular:
            continue  # >1 km, F4-1 bunu yeni istasyon olarak yazdi
        api_komsulari[row["id"]] = (row, komsular)
        for canli_id, mesafe in komsular:
            canli_komsulari[canli_id].append((row["id"], mesafe))

    canli_by_id = {r["id"]: r for r in live}

    eslesme, belirsiz = [], []
    for api_id, (row, komsular) in api_komsulari.items():
        if len(komsular) != 1:
            belirsiz.append((row, f"{len(komsular)} canli komsu"))
            continue
        canli_id, mesafe = komsular[0]
        if len(canli_komsulari[canli_id]) != 1:
            belirsiz.append((row, f"canli kaydin {len(canli_komsulari[canli_id])} API komsusu var"))
            continue

        # Yakinlik tek basina yetmez: eski kaydin GERCEK bir ticari unvani
        # varsa ve API'deki unvan ona benzemiyorsa, bunlar ayri isletme
        # olabilir. Ustune yazmak geri alinamaz kimlik kaybi demektir.
        eski = canli_by_id[canli_id]
        eski_isim = eski.get("isim") or ""
        api_isim = row.get("name") or ""
        if not _jenerik_isim(eski_isim) and not _ayni_isletme(eski_isim, api_isim):
            belirsiz.append((
                row,
                f"unvan uyusmuyor ({mesafe:.0f} m): {eski_isim[:28]!r}",
            ))
            continue

        eslesme.append((row, canli_id, mesafe))

    print(f"=== F4-2: karantina zenginlestirme "
          f"({'CANLI YAZMA' if uygula else 'DRY-RUN'}) ===\n")
    print(f"  Bantta API kaydi : {len(api_komsulari)}")
    print(f"  1-e-1 eslesme    : {len(eslesme)}")
    print(f"  Belirsiz (atlandi): {len(belirsiz)}\n")

    if eslesme:
        print("--- Zenginlestirilecek (ilk 10) ---")
        for row, canli_id, mesafe in sorted(eslesme, key=lambda t: t[2])[:10]:
            eski = canli_by_id[canli_id]
            print(f"  {mesafe:6.0f} m  {eski.get('isim')!r}")
            print(f"            -> {str(row.get('name'))[:52]!r}")
            print(f"               adres: {str(eski.get('adres') or '(yok)')[:30]!r} "
                  f"-> {str(row.get('address'))[:38]!r}")

    if belirsiz:
        print(f"\n--- Belirsiz, DOKUNULMADI (ilk 5) ---")
        for row, sebep in belirsiz[:5]:
            print(f"  {str(row.get('name'))[:44]!r} ({row.get('province')}) — {sebep}")

    if not uygula:
        print("\n[DRY] Hicbir sey yazilmadi. Yazmak icin: --uygula")
        return 0

    guncellenen, hata = 0, 0
    simdi = datetime.now(timezone.utc).isoformat()
    for row, canli_id, _ in eslesme:
        try:
            supabase.table("istasyonlar").update({
                "isim": clean_text(row.get("name")),
                "adres": clean_text(row.get("address")) or None,
                "il": normalize_province(row.get("province")),
                "ilce": normalize_city(row.get("district")),
                "enlem": float(row["latitude"]),
                "boylam": float(row["longitude"]),
                "veri_kaynagi": SOURCE,
                "guncellenme_tarihi": simdi,
            }).eq("id", canli_id).execute()
            guncellenen += 1
        except Exception as exc:
            hata += 1
            print(f"[WARN] {canli_id} guncellenemedi: {exc}")

    print(f"\n[OK] {guncellenen} kayit zenginlestirildi, {hata} hata.")
    return 1 if hata else 0


if __name__ == "__main__":
    raise SystemExit(main("--uygula" in sys.argv))
