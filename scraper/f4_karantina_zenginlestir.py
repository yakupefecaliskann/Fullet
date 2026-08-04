"""Karantinadaki kayitlari ZENGINLESTIR (yeni istasyon EKLEME) — cok markali.

Envanter botlari 75 m - 1 km bandindaki kayitlari kasten yazmiyor: eski
kaydin koordinati kaba oldugu icin eslesmiyorlar ama aslinda ayni istasyon
olabilirler. Korlemesine eklemek kopya uretir.

Bu arac o bandi ikinci kez, DAHA SIKI olculerle degerlendirir ve eslesenlerde
eski kaydin uzerine gercek unvan + tam adres + kesin koordinat yazar.
Koordinat guncellendigi icin kayit bir sonraki kosuda <75 m eslesir ve
karantina bandindan kalici olarak cikar.

--- IKI KATMANLI GUVENLIK ---------------------------------------------------

1. 1-e-1 KURALI: API kaydinin bantta tek canli komsusu olmali VE o canli
   kaydin da bantta tek API komsusu olmali. Aksi halde hangisinin hangisi
   oldugu belirsizdir. ("YAGLI BATI"/"YAGLI DOGU" vakasi.)

2. UNVAN DOGRULAMASI: yakinlik tek basina yetmiyor. Canli olcumde 1-e-1
   kurali gecen ama unvani uyusmayan ciftler cikti ve ikisi de farkli
   mahalledeydi:

       'PARMAKSIZLAR PETROL' (EFELER MAH. NO:6)
           <-> 'OZTURKLER ENERJI' (CUMHURIYET MAH. NO:42/1)   159 m
       'GOKMENOGLU MADENCILIK' (KALEKAPU MAH.)
           <-> 'GKM AKARYAKIT' (ERENLER MAH.)                  180 m

   Bunlar buyuk olasilikla AYRI istasyonlar; ustune yazmak iki istasyonu tek
   kayda ezer ve GERI ALINAMAZ. Eski kayit jenerik isimliyse (ornegin
   'Opet Inegol') kaybedilecek kimlik yoktur, yazilir; gercek bir unvani
   varsa fuzzy eslesme sart.

Kullanim:
    python f4_karantina_zenginlestir.py                 # dry-run, tum markalar
    python f4_karantina_zenginlestir.py --uygula        # canliya yazar
    python f4_karantina_zenginlestir.py --marka Opet    # tek marka
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timezone

from db_utils import supabase
from matching import StationProximityIndex, _fuzzy_match_name, _haversine
from normalization import clean_text, normalize_city, normalize_province
from station_inventory_common import KARANTINA_ALT_KM, KARANTINA_UST_KM, gecerli_konum

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def _opet_kayitlari():
    import opet_station_bot as bot
    from http_utils import HTTP
    rows = HTTP.post(bot.API_URL, headers=bot.HEADERS, json={}, timeout=(5, 60)).json()
    return bot.SOURCE, [
        {
            "isim": r.get("name"), "adres": r.get("address"),
            "il": r.get("province"), "ilce": r.get("district"),
            "lat": r.get("latitude"), "lon": r.get("longitude"),
        }
        for r in rows
    ]


def _po_kayitlari():
    import po_station_bot as bot
    from http_utils import HTTP
    html = HTTP.get(bot.PAGE_URL, headers=bot.HEADERS, timeout=(5, 60)).text
    return bot.SOURCE, [
        {
            "isim": r.get("StationName"), "adres": r.get("Address"),
            "il": r.get("CityName"), "ilce": r.get("DistrictName"),
            "lat": r.get("Latitude"), "lon": r.get("Longitude"),
        }
        for r in bot._sayfadan_istasyonlari_cikar(html)
    ]


def _aytemiz_kayitlari():
    import aytemiz_station_bot as bot
    from http_utils import HTTP
    html = HTTP.get(bot.PAGE_URL, headers=bot.HEADERS, timeout=(5, 60)).text
    return bot.SOURCE, [
        {
            "isim": r.get("Title"), "adres": r.get("Address"),
            "il": r.get("City"), "ilce": r.get("County"),
            "lat": bot._koordinat(r.get("Lat")), "lon": bot._koordinat(r.get("Lon")),
        }
        for r in bot._sayfadan_istasyonlari_cikar(html)
    ]


KAYNAKLAR = {
    "Opet": _opet_kayitlari,
    "Petrol Ofisi": _po_kayitlari,
    "Aytemiz": _aytemiz_kayitlari,
}


def _jenerik_isim(isim: str, marka: str) -> bool:
    """Eski kayit kimliksiz mi? ('Opet Inegol' gibi marka + yer etiketi)"""
    temiz = (isim or "").strip().casefold()
    return not temiz or temiz.startswith(marka.strip().casefold())


def _canli_kayitlar(marka):
    rows, start = [], 0
    while True:
        page = (
            supabase.table("istasyonlar")
            .select("id,isim,il,ilce,adres,enlem,boylam")
            .eq("marka", marka).eq("aktif", True)
            .order("id").range(start, start + 999).execute().data or []
        )
        rows.extend(page)
        if len(page) < 1000:
            break
        start += 1000
    return rows


def marka_isle(marka: str, uygula: bool) -> tuple[int, int]:
    kaynak, ham = KAYNAKLAR[marka]()
    canli = _canli_kayitlar(marka)
    canli_pts = [
        (r, float(r["enlem"]), float(r["boylam"]))
        for r in canli
        if r.get("enlem") is not None and r.get("boylam") is not None
    ]
    canli_by_id = {r["id"]: r for r in canli}

    near = StationProximityIndex(radius_meters=KARANTINA_ALT_KM * 1000)
    for _, lat, lon in canli_pts:
        near.add(marka, lat, lon, "x")

    api_komsulari, canli_komsulari = {}, defaultdict(list)
    for idx, row in enumerate(ham):
        lat, lon = row.get("lat"), row.get("lon")
        if lat in (None, "") or lon in (None, ""):
            continue
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            continue
        if not gecerli_konum(row.get("il"), row.get("ilce")):
            continue
        if near.find(marka, lat, lon):
            continue  # zaten <75 m, bot yazdi

        komsular = [
            (r["id"], _haversine(lat, lon, a, b) * 1000)
            for r, a, b in canli_pts
            if _haversine(lat, lon, a, b) <= KARANTINA_UST_KM
        ]
        if not komsular:
            continue  # >1 km, bot yeni istasyon olarak yazdi
        api_komsulari[idx] = (row, lat, lon, komsular)
        for canli_id, mesafe in komsular:
            canli_komsulari[canli_id].append(idx)

    eslesme, belirsiz = [], 0
    for idx, (row, lat, lon, komsular) in api_komsulari.items():
        if len(komsular) != 1:
            belirsiz += 1
            continue
        canli_id, mesafe = komsular[0]
        if len(canli_komsulari[canli_id]) != 1:
            belirsiz += 1
            continue
        eski_isim = canli_by_id[canli_id].get("isim") or ""
        if not _jenerik_isim(eski_isim, marka) and not _fuzzy_match_name(
            eski_isim, row.get("isim") or ""
        ):
            belirsiz += 1
            continue
        eslesme.append((row, lat, lon, canli_id, mesafe))

    print(f"\n=== {marka} ===")
    print(f"  bantta API kaydi : {len(api_komsulari)}")
    print(f"  1-e-1 + unvan OK : {len(eslesme)}")
    print(f"  belirsiz (atlandi): {belirsiz}")
    for row, _, _, canli_id, mesafe in sorted(eslesme, key=lambda t: t[4])[:5]:
        print(f"    {mesafe:6.0f} m  {canli_by_id[canli_id].get('isim')!r}")
        print(f"              -> {str(row.get('isim'))[:52]!r}")

    if not uygula:
        return len(eslesme), 0

    guncellenen, hata = 0, 0
    simdi = datetime.now(timezone.utc).isoformat()
    for row, lat, lon, canli_id, _ in eslesme:
        try:
            supabase.table("istasyonlar").update({
                "isim": clean_text(row.get("isim")),
                "adres": clean_text(row.get("adres")) or None,
                "il": normalize_province(row.get("il")),
                "ilce": normalize_city(row.get("ilce")),
                "enlem": lat, "boylam": lon,
                "veri_kaynagi": kaynak,
                "guncellenme_tarihi": simdi,
            }).eq("id", canli_id).execute()
            guncellenen += 1
        except Exception as exc:
            hata += 1
            print(f"  [WARN] {canli_id}: {exc}")
    print(f"  -> {guncellenen} zenginlestirildi, {hata} hata")
    return len(eslesme), hata


def main() -> int:
    uygula = "--uygula" in sys.argv
    markalar = list(KAYNAKLAR)
    if "--marka" in sys.argv:
        markalar = [sys.argv[sys.argv.index("--marka") + 1]]

    print(f"=== F4 karantina zenginlestirme "
          f"({'CANLI YAZMA' if uygula else 'DRY-RUN'}) ===")
    toplam, hatalar = 0, 0
    for marka in markalar:
        try:
            adet, hata = marka_isle(marka, uygula)
            toplam += adet
            hatalar += hata
        except Exception as exc:
            print(f"\n[WARN] {marka} islenemedi: {type(exc).__name__}: {exc}")
            hatalar += 1

    print(f"\nTOPLAM aday: {toplam}")
    if not uygula:
        print("[DRY] Hicbir sey yazilmadi. Yazmak icin: --uygula")
    return 1 if hatalar else 0


if __name__ == "__main__":
    raise SystemExit(main())
