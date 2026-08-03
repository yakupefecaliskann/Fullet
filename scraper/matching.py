from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from config import supabase, ISTANBUL_REGION_DISTRICTS
from normalization import clean_text, normalize_city, parse_coordinate

def _station_district_in_istanbul_region(district: Any, region: str) -> bool:
    normalized = normalize_city(district)
    return normalized in ISTANBUL_REGION_DISTRICTS.get(region, set())

import math
import difflib

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def _fuzzy_match_name(name1: str, name2: str, return_ratio: bool = False) -> float | bool:
    if not name1 or not name2:
        return 0.0 if return_ratio else False
        
    def _strip_suffixes(n: str) -> str:
        s = n.upper()
        for suffix in ["PETROLU", "PETROLLERİ", "PETROLLERI", "PETROL", "AKARYAKIT", "A.Ş.", "A.S.", "A.Ş", "A.S", "AŞ", "AS", "SAN.", "TİC.", "TIC.", "LTD.", "ŞTİ.", "STI."]:
            s = s.replace(suffix, "")
        return s.strip()

    n1 = _strip_suffixes(name1)
    n2 = _strip_suffixes(name2)
    
    if n1 and n1 == n2:
        return 1.0 if return_ratio else True
        
    ratio = difflib.SequenceMatcher(None, n1, n2).ratio()
    if return_ratio:
        return ratio
    return ratio > 0.85

def _station_targets(item: dict[str, Any]) -> list[dict[str, Any]]:
    assert supabase is not None
    brand = item["marka"]
    city = item["il"]
    district = item["ilce"]

    if item.get("enlem") is None or item.get("boylam") is None or not item["isim"]:
        query = (
            supabase.table("istasyonlar")
            .select("id,isim,ilce")
            .eq("marka", brand)
            .eq("il", city)
            .not_.ilike("isim", "%Fullet Verisi%")
        )
        if city == "ISTANBUL" and district in ISTANBUL_REGION_DISTRICTS:
            pass
        elif district:
            query = query.ilike("ilce", f"%{district}%")
        targets = query.execute().data or []
        if city == "ISTANBUL" and district in ISTANBUL_REGION_DISTRICTS:
            targets = [
                target
                for target in targets
                if _station_district_in_istanbul_region(target.get("ilce"), district)
            ]
        if targets:
            station_ids = [target["id"] for target in targets]
            from database_writes import _chunks
            for batch in _chunks(station_ids):
                supabase.table("istasyonlar").update({
                    "veri_kaynagi": item["veri_kaynagi"],
                    "aktif": True, # Keep for backward compatibility
                    "visibility_status": "visible",
                    "guncellenme_tarihi": datetime.now(timezone.utc).isoformat(),
                }).in_("id", batch).execute()
        return targets

    # 1. Exact Match Attempt
    existing = (
        supabase.table("istasyonlar")
        .select("id,enlem,boylam,isim")
        .eq("marka", brand)
        .eq("isim", item["isim"])
        .limit(1)
        .execute()
    )
    
    station_id = None
    if existing.data:
        station_id = existing.data[0]["id"]
    
    # 2. Koordinat Öncelikli Eşleştirme
    # Eğer item'ın koordinatı varsa, önce 500 metre içindeki istasyonu ara.
    # Bu, aynı ilçede iki tane aynı marka istasyon olduğunda
    # yanlış istasyona fiyat yazılmasını önler.
    if not station_id and item.get("enlem") and item.get("boylam") and district:
        candidates = (
            supabase.table("istasyonlar")
            .select("id,enlem,boylam,isim")
            .eq("marka", brand)
            .eq("il", city)
            .ilike("ilce", f"%{district}%")
            .execute()
        ).data or []

        item_lat = item["enlem"]
        item_lng = item["boylam"]

        # Adım 1: 500m içindeki aday var mı? (Koordinat kesin eşleşme)
        coord_candidates = [
            cand for cand in candidates
            if cand.get("enlem") is not None and cand.get("boylam") is not None
            and _haversine(item_lat, item_lng, cand["enlem"], cand["boylam"]) <= 0.5
        ]
        if coord_candidates:
            # En yakın olanı seç
            coord_candidates.sort(
                key=lambda c: _haversine(item_lat, item_lng, c["enlem"], c["boylam"])
            )
            station_id = coord_candidates[0]["id"]

        # Adım 2: Koordinat eşleşmesi yoksa fuzzy isim eşleştirmesi yap
        if not station_id:
            for cand in candidates:
                distance_km = None
                if cand.get("enlem") is not None and cand.get("boylam") is not None:
                    distance_km = _haversine(item_lat, item_lng, cand["enlem"], cand["boylam"])

                ratio = _fuzzy_match_name(item["isim"], cand.get("isim", ""), return_ratio=True)

                if distance_km is not None:
                    if distance_km < 5.0 and ratio > 0.85:
                        station_id = cand["id"]
                        break
                    elif distance_km <= 15.0 and ratio > 0.95:
                        station_id = cand["id"]
                        break
                else:
                    if ratio > 0.90:
                        station_id = cand["id"]
                        break

    if station_id:
        supabase.table("istasyonlar").update({
            "il": city,
            "ilce": district,
            "adres": item.get("adres"),
            "enlem": item["enlem"],
            "boylam": item["boylam"],
            "veri_kaynagi": item["veri_kaynagi"],
            "aktif": True,
            "visibility_status": "visible",
            "guncellenme_tarihi": datetime.now(timezone.utc).isoformat(),
        }).eq("id", station_id).execute()
        return [{"id": station_id}]

    # 3. Insert New Station
    inserted = supabase.table("istasyonlar").insert({
            "marka": brand,
            "isim": item["isim"],
            "il": city,
            "ilce": district,
            "adres": item.get("adres"),
            "enlem": item["enlem"],
            "boylam": item["boylam"],
            "veri_kaynagi": item["veri_kaynagi"],
            "aktif": True,
            "visibility_status": "visible",
            "guncellenme_tarihi": datetime.now(timezone.utc).isoformat(),
    }).execute()
    return [{"id": inserted.data[0]["id"]}]

def _station_inventory_target(item: dict[str, Any]) -> str:
    assert supabase is not None
    query = (
        supabase.table("istasyonlar")
        .select("id")
        .eq("marka", item["marka"])
        .eq("isim", item["isim"])
        .eq("il", item["il"])
    )
    if item["ilce"]:
        query = query.eq("ilce", item["ilce"])

    existing = query.limit(1).execute()
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "il": item["il"],
        "ilce": item["ilce"],
        "adres": item.get("adres"),
        "enlem": item["enlem"],
        "boylam": item["boylam"],
        "veri_kaynagi": item["veri_kaynagi"],
        "guncellenme_tarihi": now,
    }

    if existing.data:
        station_id = existing.data[0]["id"]
        supabase.table("istasyonlar").update(payload).eq("id", station_id).execute()
        return station_id

    inserted = supabase.table("istasyonlar").insert({
        "marka": item["marka"],
        "isim": item["isim"],
        **payload,
        "aktif": False,
        # `aktif=False` ise `visibility_status` DAİMA 'hidden' olmalı. Bu satır
        # eskiden yoktu ve kolon varsayılanı 'visible' olduğu için canlıda 354
        # "pasif ama visible" kayıt oluşmuştu — iki bayrak birbiriyle çelişiyordu.
        # Tek kural: durum bayrağı ile görünürlük bayrağı ASLA çelişmez.
        "visibility_status": "hidden",
        "olusturulma_tarihi": now,
    }).execute()
    return inserted.data[0]["id"]

def _station_inventory_key(item: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        item["marka"],
        clean_text(item["isim"]),
        normalize_city(item["il"]),
        normalize_city(item["ilce"]),
    )

# --- İstasyon kimliği: yakınlık eşleştirmesi ---------------------------------
#
# Eski `_station_inventory_coord_key` bir KOVA idi: (marka, il, ilce,
# round(lat,4), round(lon,4)). `round(...,4)` ≈ 11 m, dolayısıyla aynı fiziksel
# istasyonun 12 m farkla kaydedilmiş iki sürümü FARKLI kovalara düşüp "ayrı
# istasyon" sayılıyordu. Canlı ölçüm (3 Ağu 2026): 100 aktif kopya çifti,
# aralarındaki mesafeler 0–12 m; 98'inde ikisinde de fiyat vardı (bölünmüş
# veri), 6'sı aynı yakıtta FARKLI fiyat gösteriyordu. Kaynak dağılımı suçu
# gösterdi: 66 çift Shell'in fiyat botunun KENDİSİYLE çakışmasıydı.
#
# İkinci kusur: anahtarda `il`/`ilce` vardı. Aynı istasyon bir koşuda
# ilce='' , diğerinde ilce='ÇEKMEKÖY' ile gelince yine kopya üretiliyordu.
# İdari alanlar bu veri setinde güvenilir değil (bkz. Faz 3 taban ölçümü);
# kimlik yalnızca MARKA + KONUM olmalı.
STATION_MATCH_RADIUS_METERS = 75.0

# Hücre kenarı yarıçaptan büyük seçilir ve 3x3 komşuluk taranır; böylece kova
# SINIRINDA duran çiftler de bulunur (kova-eşitliğinin asıl kırıldığı yer).
_PROXIMITY_CELL_DEGREES = 0.01  # ~1,1 km


class StationProximityIndex:
    """Marka + konuma göre "bu istasyonu zaten tanıyor muyuz?" indeksi."""

    def __init__(self, radius_meters: float = STATION_MATCH_RADIUS_METERS) -> None:
        self._radius_km = radius_meters / 1000.0
        self._cells: dict[tuple[str, int, int], list[tuple[float, float, str]]] = {}

    @staticmethod
    def _cell(latitude: float, longitude: float) -> tuple[int, int]:
        return (
            int(math.floor(latitude / _PROXIMITY_CELL_DEGREES)),
            int(math.floor(longitude / _PROXIMITY_CELL_DEGREES)),
        )

    def add(self, brand: Any, latitude: float, longitude: float, station_id: str) -> None:
        row, col = self._cell(latitude, longitude)
        self._cells.setdefault((clean_text(brand), row, col), []).append(
            (latitude, longitude, station_id)
        )

    def find(self, brand: Any, latitude: float, longitude: float) -> str | None:
        """Yarıçap içindeki EN YAKIN istasyonun id'si (yoksa None)."""
        brand_key = clean_text(brand)
        row, col = self._cell(latitude, longitude)
        best_id: str | None = None
        best_distance = self._radius_km
        for drow in (-1, 0, 1):
            for dcol in (-1, 0, 1):
                for other_lat, other_lon, station_id in self._cells.get(
                    (brand_key, row + drow, col + dcol), ()
                ):
                    distance = _haversine(latitude, longitude, other_lat, other_lon)
                    if distance <= best_distance:
                        best_distance = distance
                        best_id = station_id
        return best_id


def station_coordinates(item: dict[str, Any]) -> tuple[float, float] | None:
    latitude = parse_coordinate(item.get("enlem"), latitude=True)
    longitude = parse_coordinate(item.get("boylam"), latitude=False)
    if latitude is None or longitude is None:
        return None
    return latitude, longitude


def _existing_station_inventory_indexes(
    brands: Iterable[str],
) -> tuple[dict[tuple[str, str, str, str], str], StationProximityIndex]:
    """(isim tabanlı indeks, konum tabanlı yakınlık indeksi).

    İkincisi eskiden `round(coord, 4)` kovalı bir dict'ti; 11 m'lik kova aynı
    istasyonun 12 m farklı iki kaydını ayrı sanıyordu ve canlıda 100 kopya
    çifti üretmişti (bkz. StationProximityIndex).
    """
    assert supabase is not None
    existing_by_key: dict[tuple[str, str, str, str], str] = {}
    proximity = StationProximityIndex()
    for brand in sorted(set(brands)):
        start = 0
        while True:
            rows = (
                supabase.table("istasyonlar")
                .select("id,marka,isim,il,ilce,enlem,boylam")
                .eq("marka", brand)
                .order("id")
                .range(start, start + 999)
                .execute()
                .data
                or []
            )
            for row in rows:
                key = (
                    clean_text(row.get("marka")),
                    clean_text(row.get("isim")),
                    normalize_city(row.get("il")),
                    normalize_city(row.get("ilce")),
                )
                existing_by_key.setdefault(key, row["id"])
                coordinates = station_coordinates(row)
                if coordinates is not None:
                    proximity.add(row.get("marka"), coordinates[0], coordinates[1], row["id"])
            if len(rows) < 1000:
                break
            start += 1000
    return existing_by_key, proximity

def _regional_targets_from_loaded(
    item: dict[str, Any],
    stations_by_brand_city: dict[tuple[str, str], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    targets = stations_by_brand_city.get((item["marka"], item["il"]), [])
    district = item.get("ilce")
    if item["il"] == "ISTANBUL" and district in ISTANBUL_REGION_DISTRICTS:
        return [
            target
            for target in targets
            if _station_district_in_istanbul_region(target.get("ilce"), district)
        ]
    if district:
        return [
            target
            for target in targets
            if district in clean_text(target.get("_normalized_district"))
        ]
    return targets
