"""F4-0 teshis: eslesmeyen 121 Opet kaydi NEDEN eslesmedi?

Iki olasilik ayirt edilir:
  (a) koordinat kabaligi  -> API'de yakinda (75 m - 2 km) bir istasyon VAR,
                             eski kayit ilce merkezine yuvarlanmis olabilir
  (b) gercekten yok       -> en yakin API istasyonu km'lerce uzakta;
                             istasyon kapanmis veya kayit hatali

Karar bu dagilimdan cikar. HICBIR SEY YAZMAZ.
"""
from __future__ import annotations

import math
import sys

import requests

from db_utils import supabase
from matching import StationProximityIndex

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


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def main():
    api_rows = requests.post(API, headers=HEADERS, json={}, timeout=60).json()
    api_pts = [
        (float(r["latitude"]), float(r["longitude"]), r.get("name", ""), r.get("province", ""))
        for r in api_rows
        if r.get("latitude") and r.get("longitude")
    ]

    live, start = [], 0
    while True:
        page = (
            supabase.table("istasyonlar")
            .select("id,isim,il,ilce,enlem,boylam")
            .eq("marka", "Opet").eq("aktif", True)
            .order("id").range(start, start + 999).execute().data or []
        )
        live.extend(page)
        if len(page) < 1000:
            break
        start += 1000

    index = StationProximityIndex()
    for lat, lon, name, _ in api_pts:
        if not index.find("Opet", lat, lon):
            index.add("Opet", lat, lon, name)

    kovalar = {"<75m (eslesti)": 0, "75-250m": 0, "250m-1km": 0, "1-5km": 0, ">5km": 0}
    ornekler = {"75-250m": [], "250m-1km": [], "1-5km": [], ">5km": []}

    for row in live:
        lat, lon = row.get("enlem"), row.get("boylam")
        if lat is None or lon is None:
            continue
        lat, lon = float(lat), float(lon)
        if index.find("Opet", lat, lon):
            kovalar["<75m (eslesti)"] += 1
            continue
        en_yakin = min(
            ((haversine_m(lat, lon, a, b), nm, pv) for a, b, nm, pv in api_pts),
            key=lambda t: t[0],
        )
        d = en_yakin[0]
        kova = "75-250m" if d < 250 else "250m-1km" if d < 1000 else "1-5km" if d < 5000 else ">5km"
        kovalar[kova] += 1
        if len(ornekler[kova]) < 5:
            ornekler[kova].append(
                f"{row.get('isim')!r} {row.get('il')}/{row.get('ilce')} "
                f"-> en yakin API: {en_yakin[1][:40]!r} ({d:.0f} m)"
            )

    print("=== Eslesmeyen Opet kayitlarinin API'ye mesafesi ===\n")
    toplam = sum(kovalar.values())
    for k, v in kovalar.items():
        pay = (v / toplam * 100) if toplam else 0
        print(f"  {k:16} {v:4}  (%{pay:.1f})")

    for kova, satirlar in ornekler.items():
        if satirlar:
            print(f"\n--- {kova} ornekleri ---")
            for s in satirlar:
                print("   ", s)


if __name__ == "__main__":
    main()
