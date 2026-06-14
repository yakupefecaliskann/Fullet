from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Iterable

import requests

from config import supabase, SUPABASE_URL, SUPABASE_KEY, CANONICAL_FUELS, ISTANBUL_REGION_DISTRICTS, is_write_allowed, is_dry_run
from matching import _station_inventory_coord_key, _station_inventory_key, _existing_station_inventory_indexes, _station_targets, _regional_targets_from_loaded
from normalization import clean_text, normalize_city
from models import SaveSummary

def _chunks(items: list[Any], size: int = 100) -> Iterable[list[Any]]:
    for index in range(0, len(items), size):
        yield items[index:index + size]

def _bulk_upsert_prices(rows: list[dict[str, Any]]) -> int:
    assert supabase is not None
    if not rows:
        return 0

    deduped_rows = {
        (row["istasyon_id"], row["yakit_tipi"]): row
        for row in rows
    }
    unique_rows = list(deduped_rows.values())

    station_ids = list(set(row["istasyon_id"] for row in unique_rows))
    existing_prices = {}
    
    # Fetch existing prices for zero-cost diffing
    for batch in _chunks(station_ids, 200):
        try:
            res = (
                supabase.table("fiyatlar")
                .select("istasyon_id, yakit_tipi, fiyat, price_status, son_guncelleme")
                .in_("istasyon_id", batch)
                .execute()
            )
            for r in (res.data or []):
                existing_prices[(r["istasyon_id"], r["yakit_tipi"])] = r
        except Exception as exc:
            print(f"[WARN] Failed to fetch existing prices for diffing: {exc}")

    now_utc = datetime.now(timezone.utc)
    rows_to_upsert = []

    for row in unique_rows:
        key = (row["istasyon_id"], row["yakit_tipi"])
        existing = existing_prices.get(key)

        if existing:
            # Check if price changed
            if float(existing.get("fiyat", 0)) != float(row.get("fiyat", 0)):
                row["price_status"] = "fresh"
                rows_to_upsert.append(row)
                continue

            # Check if status is not fresh
            if existing.get("price_status") != "fresh":
                row["price_status"] = "fresh"
                rows_to_upsert.append(row)
                continue

            # Check if it needs a freshness bump (older than 24 hours)
            son_guncelleme = existing.get("son_guncelleme")
            if son_guncelleme:
                try:
                    # Handle ISO format parsing
                    parsed_date = datetime.fromisoformat(son_guncelleme.replace("Z", "+00:00"))
                    if (now_utc - parsed_date).total_seconds() > 86400: # 24 hours
                        row["price_status"] = "fresh"
                        rows_to_upsert.append(row)
                        continue
                except ValueError:
                    row["price_status"] = "fresh"
                    rows_to_upsert.append(row)
                    continue
                    
            # Unchanged and fresh -> SKIP! (Zero-Cost!)
        else:
            # Completely new row
            row["price_status"] = "fresh"
            rows_to_upsert.append(row)

    if not rows_to_upsert:
        return 0

    try:
        for batch in _chunks(rows_to_upsert, 500):
            supabase.table("fiyatlar").upsert(
                batch,
                on_conflict="istasyon_id,yakit_tipi",
            ).execute()
    except Exception as exc:
        if "veri_kaynagi" not in str(exc):
            raise
        print("[WARN] fiyatlar.veri_kaynagi is missing; run database/production_hardening.sql for source traceability.")
        fallback_rows = [
            {key: value for key, value in row.items() if key != "veri_kaynagi"}
            for row in rows_to_upsert
        ]
        for batch in _chunks(fallback_rows, 500):
            supabase.table("fiyatlar").upsert(
                batch,
                on_conflict="istasyon_id,yakit_tipi",
            ).execute()
            
    return len(rows_to_upsert)

def _bulk_write_station_inventory(items: list[dict[str, Any]]) -> int:
    assert supabase is not None
    if not items:
        return 0

    deduped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in items:
        dedupe_key = _station_inventory_coord_key(item) or _station_inventory_key(item)
        deduped[dedupe_key] = item

    now = datetime.now(timezone.utc).isoformat()
    existing_by_key, existing_by_coord = _existing_station_inventory_indexes(
        item["marka"] for item in deduped.values()
    )
    updates: list[dict[str, Any]] = []
    inserts: list[dict[str, Any]] = []

    for key, item in deduped.items():
        payload = {
            "marka": item["marka"],
            "isim": item["isim"],
            "il": item["il"],
            "ilce": item["ilce"],
            "adres": item.get("adres"),
            "enlem": item["enlem"],
            "boylam": item["boylam"],
            "veri_kaynagi": item["veri_kaynagi"],
            "guncellenme_tarihi": now,
        }
        coord_key = _station_inventory_coord_key(item)
        station_id = existing_by_key.get(key)
        if station_id is None:
            for match_name in item.get("eslesme_isimleri", []):
                match_key = (
                    item["marka"],
                    clean_text(match_name),
                    normalize_city(item["il"]),
                    normalize_city(item["ilce"]),
                )
                station_id = existing_by_key.get(match_key)
                if station_id is not None:
                    break
        if station_id is None and coord_key is not None:
            station_id = existing_by_coord.get(coord_key)
        if station_id:
            updates.append({"id": station_id, **payload, "visibility_status": "low_priority", "aktif": True})
        else:
            inserts.append({
                **payload,
                "aktif": True,
                "visibility_status": "low_priority",
                "olusturulma_tarihi": now,
            })

    updates_by_id = {row["id"]: row for row in updates}
    inserts_by_coord: dict[tuple[float, float], dict[str, Any]] = {}
    inserts_without_coord: list[dict[str, Any]] = []
    for row in inserts:
        coord_key = _station_inventory_coord_key(row)
        if coord_key is None:
            inserts_without_coord.append(row)
        else:
            inserts_by_coord[(coord_key[-2], coord_key[-1])] = row

    unique_updates = list(updates_by_id.values())
    unique_inserts = list(inserts_by_coord.values()) + inserts_without_coord

    for batch in _chunks(unique_updates, 500):
        supabase.table("istasyonlar").upsert(batch, on_conflict="id").execute()
    for batch in _chunks(unique_inserts, 500):
        supabase.table("istasyonlar").insert(batch).execute()

    return len(unique_updates) + len(unique_inserts)

def _mark_unreported_prices_unknown(station_ids: list[str], fuels: set[str]) -> int:
    assert supabase is not None
    updated = 0
    if not station_ids:
        return updated
    for fuel in CANONICAL_FUELS:
        if fuel in fuels:
            continue
        for batch in _chunks(station_ids, 200):
            try:
                response = (
                    supabase.table("fiyatlar")
                    .update({"price_status": "unknown"})
                    .in_("istasyon_id", batch)
                    .eq("yakit_tipi", fuel)
                    .neq("price_status", "unknown")
                    .execute()
                )
                updated += len(response.data or [])
            except Exception as exc:
                print(f"[WARN] unknown price status update failed for {fuel}: {exc}")
    return updated

def _reset_split_region_targets(items: list[dict[str, Any]]) -> None:
    assert supabase is not None
    reset_groups = {
        (item["marka"], item["il"])
        for item in items
        if item.get("veri_kapsami") == "regional_official"
        and item.get("il") == "ISTANBUL"
        and item.get("ilce") in ISTANBUL_REGION_DISTRICTS
    }
    for brand, city in sorted(reset_groups):
        supabase.table("istasyonlar").update({
            "aktif": False,
            "guncellenme_tarihi": datetime.now(timezone.utc).isoformat(),
        }).eq("marka", brand).eq("il", city).not_.ilike(
            "isim", "%Fullet Verisi%"
        ).execute()
        print(f"[INFO] Reset {brand} {city} before split-region price write.")

def _load_brand_stations(brands: Iterable[str]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    assert supabase is not None
    stations_by_brand_city: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for brand in sorted(set(brands)):
        start = 0
        while True:
            rows = (
                supabase.table("istasyonlar")
                .select("id,marka,isim,il,ilce,enlem,boylam")
                .eq("marka", brand)
                .not_.ilike("isim", "%Fullet Verisi%")
                .range(start, start + 999)
                .execute()
                .data
                or []
            )
            for row in rows:
                normalized_city = normalize_city(row.get("il"))
                normalized_district = normalize_city(row.get("ilce"))
                row["_normalized_city"] = normalized_city
                row["_normalized_district"] = normalized_district
                stations_by_brand_city.setdefault((brand, normalized_city), []).append(row)
            if len(rows) < 1000:
                break
            start += 1000
    return stations_by_brand_city

def send_summary_push(message: str, is_zam: bool = False) -> None:
    if not (SUPABASE_URL and SUPABASE_KEY):
        print("[WARN] Push skipped: Supabase env values are missing.")
        return
    try:
        response = requests.post(
            f"{SUPABASE_URL}/functions/v1/fiyat-push",
            headers={
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "action": "SUMMARY_PUSH",
                "isZam": bool(is_zam),
                "message": message[:240],
            },
            timeout=10,
        )
        if response.ok:
            print("[OK] Summary push accepted.")
        else:
            print(f"[WARN] Push service returned {response.status_code}: {response.text[:200]}")
    except Exception as exc:
        print(f"[WARN] Push failed: {exc}")
