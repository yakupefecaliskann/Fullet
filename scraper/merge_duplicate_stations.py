"""Aynı fiziksel istasyonun birden fazla kaydını birleştirir (Faz 3 / F3-1).

Varsayılan DRY-RUN'dır. Yazmak için `FULLET_ALLOW_DB_WRITE=1`.

--- Neden gerekli? -----------------------------------------------------------

`_station_inventory_coord_key` bir KOVA idi: (marka, il, ilce, round(lat,4),
round(lon,4)). `round(...,4)` ≈ 11 m, dolayısıyla aynı fiziksel istasyonun
12 m farkla kaydedilmiş iki sürümü FARKLI kovalara düşüp "ayrı istasyon"
sayılıyordu. Anahtarda `il`/`ilce` de vardı; aynı istasyon bir koşuda
ilce='', diğerinde ilce='ÇEKMEKÖY' ile gelince yine kopya üretiliyordu.

Canlı ölçüm (3 Ağustos 2026): 101 aktif kopya çifti, 98'inde ikisinde de
fiyat vardı (bölünmüş veri), **6'sı aynı yakıtta FARKLI fiyat gösteriyordu**
— kullanıcı aynı istasyonu haritada iki pinde iki fiyatla görüyordu.

Üretim tarafı `matching.StationProximityIndex` ile düzeltildi (yeni kopya
oluşmuyor). Bu script MEVCUT kopyaları temizler.

--- Yarıçap neden 75 m? ------------------------------------------------------

101 canlı çift üzerinde ölçüldü:

    0-25 m   63 çift ┐
    25-50 m  13 çift ├ birleştirilir
    50-75 m   2 çift ┘
    75-150 m 23 çift  -> KASITLI olarak birleştirilmez

75 m üstündekilerin çoğu kopya DEĞİL: 'ORHANGAZİ-BATI'/'ORHANGAZİ-DOĞU'
(127 m), 'YAĞLI BATI'/'YAĞLI DOĞU' (101 m), 'POLATLI BATI'/'POLATLI DOĞU'
(109 m) — yol ayrımının iki yanındaki AYRI istasyonlar. Yarıçapı büyütmek
bunları yanlışlıkla birleştirirdi (D4 dersi: 2,4 km uzaktakiler kopya değildi).

--- Hangi kayıt yaşar? -------------------------------------------------------

1. Jenerik olmayan isim ('ÇEKMEKÖY AKÇEŞME.' > 'Shell')
2. Daha çok TAZE fiyatı olan
3. Daha eski `olusturulma_tarihi` (asıl kayıt)
4. id (belirlenimci olsun diye)

Fiyatlar yakıt bazında birleştirilir: fresh > stale > unknown, eşitlikte
`son_dogrulama` yenisi kazanır. Favoriler (`fullet_favorites`) ve fiyat
alarmları (`price_alerts`) SİLMEDEN ÖNCE hayatta kalana taşınır —
`ON DELETE CASCADE` yüzünden aksi hâlde sessizce kaybolurlardı.
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from config import BRAND_ALIASES, supabase
from freshness import parse_timestamp
from matching import STATION_MATCH_RADIUS_METERS, _haversine, station_coordinates
from normalization import clean_text

_STATUS_RANK = {"fresh": 3, "stale": 2, "unknown": 1}

# İkinci kademe: 75-150 m arası YALNIZCA taraflardan biri jenerik isimliyse
# birleştirilir. Jenerik isim ('Shell', 'Total') fiyat botunun ürettiği bir
# artefakttır — gerçek bir istasyon adı değildir; o mesafede iki GERÇEK isimli
# kayıt ise neredeyse her zaman ayrı istasyondur.
#
# Bu ayrım ölçümle doğrulandı. 75-150 m bandındaki 18 çiftin 16'sı gerçekten
# ayrı: 'YAĞLI BATI'/'YAĞLI DOĞU', 'POLATLI BATI'/'POLATLI DOĞU',
# 'DAVUTPAŞA ALTYOL'/'DAVUTPAŞA ÜSTYOL', 'KÜTAHYA-1'/'KÜTAHYA-2' — yol
# ayrımının iki yanındaki ayrı istasyonlar. Yarıçapı topyekûn 150 m'ye
# çıkarmak bunların HEPSİNİ yanlışlıkla birleştirirdi.
GENERIC_NAME_MATCH_RADIUS_METERS = 150.0


def _page_all(table: str, select: str) -> list[dict[str, Any]]:
    """Tabloyu sayfalayarak okur.

    `.order("id")` ŞART: `ORDER BY` olmadan sayfalama Postgres'te garantisizdir.
    Botlar bu tablolara sürekli yazdığı için satırlar heap'te yer değiştirir ve
    aynı satır iki sayfada birden gelebilir ya da hiç gelmeyebilir. Sessiz
    veri kaybının klasik kaynağıdır; maliyeti sıfır olduğu için her yerde var.
    """
    assert supabase is not None
    rows: list[dict[str, Any]] = []
    start = 0
    while True:
        page = (
            supabase.table(table).select(select).order("id").range(start, start + 999)
            .execute().data or []
        )
        rows.extend(page)
        if len(page) < 1000:
            break
        start += 1000
    return rows


def _is_generic_name(station: dict[str, Any]) -> bool:
    """isim yalnızca marka adıysa (ör. 'Shell', 'Total') jeneriktir.

    Marka TAKMA ADLARI şart: TotalEnergies istasyonlarının bir kısmı 'Total'
    olarak kaydedilmiş ve düz `name == brand` karşılaştırması bunu jenerik
    saymıyordu — 'ALTUNİZADE 1 (11E179)' <-> 'Total' çifti bu yüzden kopya
    olarak görülmüyordu.
    """
    name = clean_text(station.get("isim")).upper()
    if not name:
        return True
    brand = clean_text(station.get("marka"))
    canonical = BRAND_ALIASES.get(name) or BRAND_ALIASES.get(name.replace(" ", ""))
    if canonical and canonical == brand:
        return True
    return name.replace(" ", "") == brand.upper().replace(" ", "")


def _generic_pair_radius_km() -> float:
    return GENERIC_NAME_MATCH_RADIUS_METERS / 1000.0


def _find_clusters(stations: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Aynı marka + yarıçap içindeki kayıtları kümeler (çift olmak zorunda değil).

    Birleşim-bul (union-find): A~B ve B~C ise üçü tek kümedir.
    """
    radius_km = STATION_MATCH_RADIUS_METERS / 1000.0
    cell_size = 0.01

    parent: dict[str, str] = {s["id"]: s["id"] for s in stations}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    cells: dict[tuple[str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for station in stations:
        latitude, longitude = station["_coord"]
        cells[(
            clean_text(station.get("marka")),
            int(latitude // cell_size),
            int(longitude // cell_size),
        )].append(station)

    for (brand, row, col), bucket in cells.items():
        neighbours: list[dict[str, Any]] = []
        for drow in (-1, 0, 1):
            for dcol in (-1, 0, 1):
                neighbours.extend(cells.get((brand, row + drow, col + dcol), ()))
        for first in bucket:
            for second in neighbours:
                if first["id"] == second["id"]:
                    continue
                distance = _haversine(*first["_coord"], *second["_coord"])
                if distance <= radius_km:
                    union(first["id"], second["id"])
                    continue
                # İkinci kademe: biri jenerik isimliyse 150 m'ye kadar.
                if distance <= _generic_pair_radius_km() and (
                    _is_generic_name(first) or _is_generic_name(second)
                ):
                    union(first["id"], second["id"])

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for station in stations:
        grouped[find(station["id"])].append(station)
    return [group for group in grouped.values() if len(group) > 1]


def _pick_survivor(
    cluster: list[dict[str, Any]], prices_by_station: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    def sort_key(station: dict[str, Any]) -> tuple:
        fresh_count = sum(
            1 for p in prices_by_station.get(station["id"], [])
            if p.get("price_status") == "fresh"
        )
        created = parse_timestamp(station.get("olusturulma_tarihi"))
        return (
            0 if station.get("aktif") else 1,             # AKTİF olan önce
            0 if not _is_generic_name(station) else 1,   # jenerik olmayan önce
            -fresh_count,                                 # çok taze fiyat önce
            created.timestamp() if created else float("inf"),  # eski kayıt önce
            str(station["id"]),
        )

    return sorted(cluster, key=sort_key)[0]


def _better_name(cluster: list[dict[str, Any]], survivor: dict[str, Any]) -> str | None:
    """Hayatta kalanın adı jenerikse ('Shell'), kümedeki gerçek adı ona taşır.

    Aktiflik isim kalitesinden ÖNCE geldiği için hayatta kalan bazen jenerik
    adlı aktif kayıt oluyor; o zaman 'ÇEKMEKÖY AKÇEŞME.' gibi gerçek ad
    silinen kayıtla birlikte kaybolurdu. Ad taşımak veriyi zenginleştirir,
    kimliği değiştirmez (kimlik marka + konum).
    """
    if not _is_generic_name(survivor):
        return None
    for station in cluster:
        if station["id"] != survivor["id"] and not _is_generic_name(station):
            return station.get("isim")
    return None


def _best_price_per_fuel(
    cluster: list[dict[str, Any]], prices_by_station: dict[str, list[dict[str, Any]]]
) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for station in cluster:
        for price in prices_by_station.get(station["id"], []):
            fuel = price.get("yakit_tipi")
            if not fuel:
                continue
            current = best.get(fuel)
            if current is None or _price_sort_key(price) > _price_sort_key(current):
                best[fuel] = price
    return best


def _price_sort_key(price: dict[str, Any]) -> tuple:
    verified = parse_timestamp(price.get("son_dogrulama"))
    return (
        _STATUS_RANK.get(price.get("price_status"), 0),
        verified.timestamp() if verified else 0.0,
    )


def main() -> int:
    if supabase is None:
        print("[FAIL] Supabase env değerleri eksik.")
        return 1

    write_enabled = os.environ.get("FULLET_ALLOW_DB_WRITE") == "1"
    mode = "UYGULAMA" if write_enabled else "DRY-RUN"
    print(f"=== İstasyon kopya birleştirme — {mode} ===")
    print(f"Yarıçap: {STATION_MATCH_RADIUS_METERS:.0f} m\n")

    stations = _page_all(
        "istasyonlar", "id,marka,isim,il,ilce,enlem,boylam,aktif,olusturulma_tarihi,veri_kaynagi"
    )
    for station in stations:
        station["_coord"] = station_coordinates(station)
    # PASİF kayıtlar da kümelenir. Bu filtre eskiden `and s.get("aktif")`
    # içeriyordu ve F3-1'in 26 kopyayı kaçırmasının sebebi tam olarak buydu:
    # bir çiftin bir üyesi birleştirme anında pasifse çift hiç görülmüyordu,
    # sonra fiyat yazma yolu (`db_utils`, `istasyonlar.aktif = True`) o kaydı
    # diriltince kopya AKTİF olarak geri geliyordu. Ölçüldü (3 Ağu 2026):
    # birleştirmeden sonra aktif istasyon 2.636 -> 2.728, üstelik arada 79
    # kayıt silinmişken. Kimlik marka + konumdur; `aktif` bir kimlik alanı
    # değil, bir durum bayrağıdır ve kopya tespitine karışmamalıdır.
    located = [s for s in stations if s["_coord"]]
    active_count = sum(1 for s in located if s.get("aktif"))
    print(f"Koordinatlı istasyon: {len(located)} / {len(stations)} "
          f"(aktif {active_count}, pasif {len(located) - active_count})")

    prices = _page_all(
        "fiyatlar", "id,istasyon_id,yakit_tipi,fiyat,price_status,son_dogrulama,son_guncelleme"
    )
    prices_by_station: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for price in prices:
        prices_by_station[price["istasyon_id"]].append(price)

    clusters = _find_clusters(located)
    if not clusters:
        print("[OK] Birleştirilecek kopya bulunamadı.")
        return 0

    doomed_ids = {s["id"] for c in clusters for s in c}
    favorites = [
        f for f in _page_all("fullet_favorites", "firebase_uid,station_id")
        if f["station_id"] in doomed_ids
    ]
    alerts = [
        a for a in _page_all("price_alerts", "id,istasyon_id")
        if a.get("istasyon_id") in doomed_ids
    ]

    print(f"Kopya kümesi: {len(clusters)}")
    print(f"Toplam kayıt: {sum(len(c) for c in clusters)}, "
          f"silinecek: {sum(len(c) - 1 for c in clusters)}")
    print(f"Taşınacak favori: {len(favorites)}, fiyat alarmı: {len(alerts)}\n")

    conflicts = 0
    planned_deletes: list[str] = []
    price_writes: list[dict[str, Any]] = []
    name_writes: list[dict[str, Any]] = []

    for index, cluster in enumerate(sorted(clusters, key=lambda c: str(c[0]["marka"])), 1):
        survivor = _pick_survivor(cluster, prices_by_station)
        losers = [s for s in cluster if s["id"] != survivor["id"]]
        best = _best_price_per_fuel(cluster, prices_by_station)

        fuel_conflicts = []
        for fuel, winner in best.items():
            values = {
                str(p.get("fiyat"))
                for s in cluster for p in prices_by_station.get(s["id"], [])
                if p.get("yakit_tipi") == fuel and p.get("fiyat") is not None
            }
            if len(values) > 1:
                fuel_conflicts.append(f"{fuel}({'/'.join(sorted(values))})")
        if fuel_conflicts:
            conflicts += 1

        distance = max(
            _haversine(*survivor["_coord"], *other["_coord"]) * 1000 for other in losers
        )
        print(f"[{index:>3}] {survivor.get('marka')} "
              f"{survivor.get('il')}/{survivor.get('ilce')}  ({distance:.0f} m)")
        print(f"      YAŞAR : {str(survivor.get('isim'))[:34]!r} "
              f"({len(prices_by_station.get(survivor['id'], []))} fiyat"
              f"{'' if survivor.get('aktif') else ', PASİF'})")
        rescued_name = _better_name(cluster, survivor)
        if rescued_name:
            name_writes.append({"id": survivor["id"], "isim": rescued_name})
            print(f"      AD    : {str(survivor.get('isim'))[:20]!r} -> {rescued_name[:30]!r}")
        for loser in losers:
            print(f"      SİL   : {str(loser.get('isim'))[:34]!r} "
                  f"({len(prices_by_station.get(loser['id'], []))} fiyat)")
            planned_deletes.append(loser["id"])
        if fuel_conflicts:
            print(f"      ÇAKIŞMA: {', '.join(fuel_conflicts)} -> taze/yeni olan kazanır")

        for fuel, winner in best.items():
            price_writes.append({
                "istasyon_id": survivor["id"],
                "yakit_tipi": fuel,
                "fiyat": winner.get("fiyat"),
                "price_status": winner.get("price_status"),
                "son_dogrulama": winner.get("son_dogrulama"),
                "son_guncelleme": winner.get("son_guncelleme"),
            })

    print(f"\nÇakışan fiyat içeren küme: {conflicts} / {len(clusters)}")

    if not write_enabled:
        print("\n[DRY-RUN] Hiçbir şey yazılmadı. Uygulamak için "
              "FULLET_ALLOW_DB_WRITE=1 ile tekrar çalıştırın.")
        return 0

    survivors_by_loser: dict[str, str] = {}
    for cluster in clusters:
        survivor = _pick_survivor(cluster, prices_by_station)
        for loser in cluster:
            if loser["id"] != survivor["id"]:
                survivors_by_loser[loser["id"]] = survivor["id"]

    # 1) Kazanan fiyatları hayatta kalana yaz (silmeden ÖNCE).
    for batch_start in range(0, len(price_writes), 200):
        supabase.table("fiyatlar").upsert(
            price_writes[batch_start:batch_start + 200],
            on_conflict="istasyon_id,yakit_tipi",
        ).execute()
    print(f"[OK] {len(price_writes)} fiyat satırı hayatta kalanlara taşındı.")

    # 1b) Jenerik adlı hayatta kalanlara kümedeki gerçek adı taşı.
    for name_row in name_writes:
        supabase.table("istasyonlar").update(
            {"isim": name_row["isim"]}
        ).eq("id", name_row["id"]).execute()
    print(f"[OK] {len(name_writes)} istasyon adı jenerikten gerçek ada taşındı.")

    # 2) Favorileri taşı (CASCADE silmeden önce). PK (firebase_uid, station_id)
    #    olduğu için hedefte aynı satır varsa insert çakışır — yok say.
    moved_favorites = 0
    for favorite in favorites:
        target = survivors_by_loser.get(favorite["station_id"])
        if not target:
            continue
        try:
            supabase.table("fullet_favorites").upsert(
                {"firebase_uid": favorite["firebase_uid"], "station_id": target},
                on_conflict="firebase_uid,station_id",
            ).execute()
            moved_favorites += 1
        except Exception as exc:
            print(f"[WARN] Favori taşınamadı ({favorite['firebase_uid']}): {exc}")
    print(f"[OK] {moved_favorites} favori taşındı.")

    moved_alerts = 0
    for alert in alerts:
        target = survivors_by_loser.get(alert["istasyon_id"])
        if not target:
            continue
        supabase.table("price_alerts").update(
            {"istasyon_id": target}
        ).eq("id", alert["id"]).execute()
        moved_alerts += 1
    print(f"[OK] {moved_alerts} fiyat alarmı taşındı.")

    # 3) Kopyaları sil (fiyatları CASCADE ile gider — kazananlar zaten taşındı).
    for batch_start in range(0, len(planned_deletes), 100):
        batch = planned_deletes[batch_start:batch_start + 100]
        supabase.table("istasyonlar").delete().in_("id", batch).execute()
    print(f"[OK] {len(planned_deletes)} kopya istasyon silindi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
