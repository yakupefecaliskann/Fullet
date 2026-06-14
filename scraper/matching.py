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

def _station_inventory_coord_key(item: dict[str, Any]) -> tuple[str, str, str, float, float] | None:
    latitude = parse_coordinate(item.get("enlem"), latitude=True)
    longitude = parse_coordinate(item.get("boylam"), latitude=False)
    if latitude is None or longitude is None:
        return None
    return (
        clean_text(item["marka"]),
        normalize_city(item["il"]),
        normalize_city(item["ilce"]),
        round(latitude, 4),
        round(longitude, 4),
    )

def _existing_station_inventory_indexes(
    brands: Iterable[str],
) -> tuple[
    dict[tuple[str, str, str, str], str],
    dict[tuple[str, str, str, float, float], str],
]:
    assert supabase is not None
    existing_by_key: dict[tuple[str, str, str, str], str] = {}
    existing_by_coord: dict[tuple[str, str, str, float, float], str] = {}
    for brand in sorted(set(brands)):
        start = 0
        while True:
            rows = (
                supabase.table("istasyonlar")
                .select("id,marka,isim,il,ilce,enlem,boylam")
                .eq("marka", brand)
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
                coord_key = _station_inventory_coord_key(row)
                if coord_key is not None:
                    existing_by_coord.setdefault(coord_key, row["id"])
            if len(rows) < 1000:
                break
            start += 1000
    return existing_by_key, existing_by_coord

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
