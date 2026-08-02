from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Iterable

# Export telemetry & models
from telemetry import record_bot_run, create_system_alert, resolve_system_alerts
from models import SaveSummary

# Export config & utilities
from config import supabase, is_dry_run, is_write_allowed, CANONICAL_FUELS, OFFICIAL_REGIONAL_SOURCES, allow_inferred_data, OFFICIAL_STATION_SOURCES
from normalization import (
    clean_text,
    normalize_city,
    normalize_brand,
    normalize_fuel,
    parse_price,
    parse_coordinate,
    istanbul_region_from_city,
    _station_district_in_istanbul_region,
)

# Export matching and db writes
from matching import _station_targets, _station_inventory_target
from database_writes import (
    _bulk_upsert_prices,
    _bulk_write_station_inventory,
    _mark_unreported_prices_unknown,
    _reset_split_region_targets,
    _load_brand_stations,
    send_summary_push,
    _regional_targets_from_loaded,
    _chunks,
)

def _apply_sanity_gate_for_brands(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Çapraz doğrulama kapısını marka bazında uygular.

    Bir koşuda birden fazla marka olabileceği için (nadiren) markalara ayrılıp
    her biri kendi referansına göre değerlendirilir.
    """
    from sanity_gate import apply_sanity_gate

    by_brand: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_brand.setdefault(item["marka"], []).append(item)

    result: list[dict[str, Any]] = []
    for brand, brand_items in by_brand.items():
        result.extend(apply_sanity_gate(brand_items, brand))
    return result


def finish_bot_run(bot_name: str, *, scraped: int, summary: SaveSummary | None = None) -> int:
    """Botun makine-okur kayıt satırını basar ve dürüst çıkış kodunu döner.

    run_all_bots.py stdout'taki [RECORDS] satırını parse edip bot_runs
    telemetrisine yazar. Scrape 0 kayıt döndürdüyse bot BAŞARISIZ sayılır
    (exit 1) — eski "boş liste + exit 0" kombinasyonu, kırık parser'ların
    aylarca 'success' görünmesine yol açıyordu (yol haritası S0-1). Yazılan
    kayıt sayısına (prices/stations) göre başarısızlık kararı VERİLMEZ:
    zero-cost diff nedeniyle değişmemiş fiyatlar meşru olarak 0 yazım üretir.
    """
    stations = summary.stations_touched if summary else 0
    prices = summary.prices_touched if summary else 0
    print(f"[RECORDS] scraped={scraped} stations={stations} prices={prices}")
    if scraped == 0:
        print(
            f"[FAIL] {bot_name}: kaynak 0 kayıt döndürdü — "
            "parser kırık veya site erişilemez."
        )
        return 1
    return 0


def normalize_scraped_item(item: dict[str, Any], default_brand: str | None = None) -> dict[str, Any] | None:
    brand = normalize_brand(item.get("marka") or item.get("brand") or item.get("istasyon_adi"), default_brand)
    raw_city = item.get("il")
    city = normalize_city(raw_city)
    district = normalize_city(item.get("ilce"))
    istanbul_region = istanbul_region_from_city(raw_city)
    if city == "ISTANBUL" and not district and istanbul_region:
        district = istanbul_region
    raw_prices = item.get("fiyatlar") or {}

    prices: dict[str, float] = {}
    if isinstance(raw_prices, dict):
        for fuel_name, raw_price in raw_prices.items():
            fuel = normalize_fuel(fuel_name)
            price = parse_price(raw_price)
            if fuel and price is not None:
                prices[fuel] = price

    if not brand or not city or not prices:
        return None

    station_name = clean_text(item.get("istasyon_adi"))
    latitude = parse_coordinate(item.get("enlem"), latitude=True)
    longitude = parse_coordinate(item.get("boylam"), latitude=False)

    source = clean_text(item.get("veri_kaynagi")) or brand
    is_official_regional = source in OFFICIAL_REGIONAL_SOURCES

    if "Fullet Verisi" in station_name:
        return None

    if not allow_inferred_data() and not is_official_regional:
        if not station_name:
            return None
        if latitude is None or longitude is None:
            return None

    if not station_name:
        station_name = ""

    return {
        "marka": brand,
        "isim": station_name,
        "il": city,
        "ilce": district,
        "adres": clean_text(item.get("adres")) or None,
        "enlem": latitude,
        "boylam": longitude,
        "fiyatlar": prices,
        "veri_kaynagi": source,
        "veri_kapsami": "regional_official" if is_official_regional and not station_name else "station_official",
    }


def normalize_scraped_data(data: Iterable[dict[str, Any]], default_brand: str | None = None) -> tuple[list[dict[str, Any]], int]:
    valid: list[dict[str, Any]] = []
    skipped = 0
    for item in data:
        normalized = normalize_scraped_item(item, default_brand=default_brand)
        if normalized is None:
            skipped += 1
        else:
            valid.append(normalized)
    return valid, skipped


def normalize_station_inventory_item(item: dict[str, Any], default_brand: str | None = None) -> dict[str, Any] | None:
    brand = normalize_brand(item.get("marka") or item.get("brand") or item.get("istasyon_adi"), default_brand)
    station_name = clean_text(item.get("istasyon_adi") or item.get("isim") or item.get("name"))
    city = normalize_city(item.get("il") or item.get("city"))
    district = normalize_city(item.get("ilce") or item.get("district") or item.get("county"))
    latitude = parse_coordinate(item.get("enlem") or item.get("lat") or item.get("latitude"), latitude=True)
    longitude = parse_coordinate(item.get("boylam") or item.get("lng") or item.get("longitude"), latitude=False)
    source = clean_text(item.get("veri_kaynagi")) or clean_text(item.get("source"))

    if not brand or not station_name or not city:
        return None
    if latitude is None or longitude is None:
        return None
    if "Fullet Verisi" in station_name:
        return None
    if source not in OFFICIAL_STATION_SOURCES:
        return None

    return {
        "marka": brand,
        "isim": station_name,
        "il": city,
        "ilce": district,
        "adres": clean_text(item.get("adres") or item.get("address")) or None,
        "enlem": latitude,
        "boylam": longitude,
        "veri_kaynagi": source,
        "eslesme_isimleri": [
            name for name in {
                station_name,
                clean_text(item.get("resmi_unvan") or item.get("official_name")),
            } if name
        ],
    }


def normalize_station_inventory_data(
    data: Iterable[dict[str, Any]],
    default_brand: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    valid: list[dict[str, Any]] = []
    skipped = 0
    for item in data:
        normalized = normalize_station_inventory_item(item, default_brand=default_brand)
        if normalized is None:
            skipped += 1
        else:
            valid.append(normalized)
    return valid, skipped


def save_regional_prices_to_supabase(
    data: Iterable[dict[str, Any]],
    *,
    default_brand: str | None = None,
    trigger_push: bool | None = None,
    dry_run: bool | None = None,
) -> SaveSummary:
    normalized, skipped = normalize_scraped_data(data, default_brand=default_brand)
    regional_items = [
        item
        for item in normalized
        if item.get("veri_kapsami") == "regional_official"
        and not item.get("isim")
        and item.get("enlem") is None
        and item.get("boylam") is None
    ]
    if len(regional_items) != len(normalized):
        return save_to_supabase(
            data,
            default_brand=default_brand,
            trigger_push=trigger_push,
            dry_run=dry_run,
        )

    dry = is_dry_run() if dry_run is None else dry_run
    brands = sorted({item["marka"] for item in normalized})
    price_count = sum(len(item["fiyatlar"]) for item in normalized)

    if dry:
        print(f"[DRY] Valid regional items: {len(normalized)}, prices: {price_count}, skipped: {skipped}, brands: {', '.join(brands) or '-'}")
        return SaveSummary(len(normalized), price_count, skipped, tuple(brands))

    if not is_write_allowed():
        print("[SAFE] DB write blocked. Set FULLET_ALLOW_DB_WRITE=1 to write live data.")
        print(f"[SAFE] Pending regional items: {len(normalized)}, prices: {price_count}, skipped: {skipped}, brands: {', '.join(brands) or '-'}")
        return SaveSummary(0, 0, skipped + len(normalized), tuple(brands))

    if not supabase:
        print("[WARN] Supabase env values are missing. Nothing was written.")
        return SaveSummary(0, 0, skipped, ())

    # Çapraz doğrulama kapısı: bir yakıtın medyanı diğer markalardan %10'dan
    # fazla sapıyorsa o yakıt yazılmaz (yol haritası S1-4).
    before = len(normalized)
    normalized = _apply_sanity_gate_for_brands(normalized)
    skipped += before - len(normalized)
    if not normalized:
        print("[WARN] Çapraz doğrulama sonrası yazılacak veri kalmadı.")
        return SaveSummary(0, 0, skipped, ())

    _reset_split_region_targets(normalized)

    refreshed_at = datetime.now(timezone.utc).isoformat()
    stations_by_brand_city = _load_brand_stations(item["marka"] for item in normalized)
    station_updates_by_source: dict[str, set[str]] = {}
    station_fuels: dict[str, set[str]] = {}
    price_rows: list[dict[str, Any]] = []
    brands_touched: set[str] = set()

    for item in normalized:
        targets = _regional_targets_from_loaded(item, stations_by_brand_city)
        if not targets:
            continue
        source = item["veri_kaynagi"]
        fuels = set(item["fiyatlar"])
        for target in targets:
            station_id = target["id"]
            station_updates_by_source.setdefault(source, set()).add(station_id)
            station_fuels.setdefault(station_id, set()).update(fuels)
            brands_touched.add(item["marka"])
            for fuel, price in item["fiyatlar"].items():
                price_rows.append({
                    "istasyon_id": station_id,
                    "yakit_tipi": fuel,
                    "fiyat": price,
                    "son_guncelleme": refreshed_at,
                    "veri_kaynagi": source,
                })

    for source, station_ids in station_updates_by_source.items():
        for batch in _chunks(sorted(station_ids), 500):
            supabase.table("istasyonlar").update({
                "veri_kaynagi": source,
                "aktif": True,
                "guncellenme_tarihi": refreshed_at,
            }).in_("id", batch).execute()

    prices_touched = _bulk_upsert_prices(price_rows)
    for fuel in CANONICAL_FUELS:
        stale_station_ids = [
            station_id
            for station_id, fuels in station_fuels.items()
            if fuel not in fuels
        ]
        for batch in _chunks(stale_station_ids, 500):
            try:
                response = (
                    supabase.table("fiyatlar")
                    .update({"price_status": "unknown"})
                    .in_("istasyon_id", batch)
                    .eq("yakit_tipi", fuel)
                    .neq("price_status", "unknown")
                    .execute()
                )
                prices_touched += len(response.data or [])
            except Exception as exc:
                print(f"[WARN] unknown price status update failed for {fuel}: {exc}")

    stations_touched = len(station_fuels)
    print(f"[OK] {stations_touched} stations and {prices_touched} prices processed. Skipped: {skipped}.")

    if trigger_push is None:
        trigger_push = os.environ.get("FULLET_PUSH_SUMMARY", "0") == "1"

    if trigger_push and stations_touched > 0:
        brand_text = ", ".join(sorted(brands_touched))
        message = f"Akaryakit fiyatlari guncellendi. {stations_touched} istasyon, {prices_touched} fiyat. {brand_text}."
        send_summary_push(message, is_zam=os.environ.get("FULLET_PUSH_IS_ZAM", "0") == "1")

    return SaveSummary(
        stations_touched=stations_touched,
        prices_touched=prices_touched,
        skipped_items=skipped,
        brands=tuple(sorted(brands_touched)),
    )


def save_to_supabase(
    data: Iterable[dict[str, Any]],
    *,
    default_brand: str | None = None,
    trigger_push: bool | None = None,
    dry_run: bool | None = None,
) -> SaveSummary:
    normalized, skipped = normalize_scraped_data(data, default_brand=default_brand)
    dry = is_dry_run() if dry_run is None else dry_run

    if dry:
        brands = sorted({item["marka"] for item in normalized})
        price_count = sum(len(item["fiyatlar"]) for item in normalized)
        print(f"[DRY] Valid items: {len(normalized)}, prices: {price_count}, skipped: {skipped}, brands: {', '.join(brands) or '-'}")
        return SaveSummary(len(normalized), price_count, skipped, tuple(brands))

    if not is_write_allowed():
        brands = sorted({item["marka"] for item in normalized})
        price_count = sum(len(item["fiyatlar"]) for item in normalized)
        print("[SAFE] DB write blocked. Set FULLET_ALLOW_DB_WRITE=1 to write live data.")
        print(f"[SAFE] Pending items: {len(normalized)}, prices: {price_count}, skipped: {skipped}, brands: {', '.join(brands) or '-'}")
        return SaveSummary(0, 0, skipped + len(normalized), tuple(brands))

    if not supabase:
        print("[WARN] Supabase env values are missing. Nothing was written.")
        return SaveSummary(0, 0, skipped, ())

    # Çapraz doğrulama kapısı (yol haritası S1-4) — bkz. sanity_gate.py
    before = len(normalized)
    normalized = _apply_sanity_gate_for_brands(normalized)
    skipped += before - len(normalized)
    if not normalized:
        print("[WARN] Çapraz doğrulama sonrası yazılacak veri kalmadı.")
        return SaveSummary(0, 0, skipped, ())

    stations_touched = 0
    prices_touched = 0
    brands_touched: set[str] = set()
    station_fuels: dict[str, set[str]] = {}

    _reset_split_region_targets(normalized)

    for item in normalized:
        try:
            targets = _station_targets(item)
            station_ids = [target["id"] for target in targets]
            refreshed_at = datetime.now(timezone.utc).isoformat()
            
            fuels = set(item["fiyatlar"])
            for station_id in station_ids:
                station_fuels.setdefault(station_id, set()).update(fuels)
                
            price_rows = [
                {
                    "istasyon_id": station_id,
                    "yakit_tipi": fuel,
                    "fiyat": price,
                    "son_guncelleme": refreshed_at,
                    "veri_kaynagi": item["veri_kaynagi"],
                }
                for station_id in station_ids
                for fuel, price in item["fiyatlar"].items()
            ]
            prices_touched += _bulk_upsert_prices(price_rows)
            stations_touched += len(station_ids)
            if station_ids:
                brands_touched.add(item["marka"])
        except Exception as exc:
            skipped += 1
            print(f"[WARN] DB write skipped for {item.get('marka')} {item.get('il')} {item.get('ilce')}: {exc}")

    for fuel in CANONICAL_FUELS:
        stale_station_ids = [
            station_id
            for station_id, fuels in station_fuels.items()
            if fuel not in fuels
        ]
        for batch in _chunks(stale_station_ids, 500):
            try:
                response = (
                    supabase.table("fiyatlar")
                    .update({"price_status": "unknown"})
                    .in_("istasyon_id", batch)
                    .eq("yakit_tipi", fuel)
                    .neq("price_status", "unknown")
                    .execute()
                )
                prices_touched += len(response.data or [])
            except Exception as exc:
                print(f"[WARN] unknown price status update failed for {fuel}: {exc}")

    print(f"[OK] {stations_touched} stations and {prices_touched} prices processed. Skipped: {skipped}.")

    if trigger_push is None:
        trigger_push = os.environ.get("FULLET_PUSH_SUMMARY", "0") == "1"

    if trigger_push and stations_touched > 0:
        brands = ", ".join(sorted(brands_touched))
        message = f"Akaryakit fiyatlari guncellendi. {stations_touched} istasyon, {prices_touched} fiyat. {brands}."
        send_summary_push(message, is_zam=os.environ.get("FULLET_PUSH_IS_ZAM", "0") == "1")

    return SaveSummary(
        stations_touched=stations_touched,
        prices_touched=prices_touched,
        skipped_items=skipped,
        brands=tuple(sorted(brands_touched)),
    )


def save_station_inventory_to_supabase(
    data: Iterable[dict[str, Any]],
    *,
    default_brand: str | None = None,
    dry_run: bool | None = None,
) -> SaveSummary:
    normalized, skipped = normalize_station_inventory_data(data, default_brand=default_brand)
    dry = is_dry_run() if dry_run is None else dry_run
    brands = sorted({item["marka"] for item in normalized})

    if dry:
        print(f"[DRY] Valid official station rows: {len(normalized)}, skipped: {skipped}, brands: {', '.join(brands) or '-'}")
        return SaveSummary(len(normalized), 0, skipped, tuple(brands))

    if not is_write_allowed():
        print("[SAFE] DB write blocked. Set FULLET_ALLOW_DB_WRITE=1 to write live station inventory.")
        print(f"[SAFE] Pending official station rows: {len(normalized)}, skipped: {skipped}, brands: {', '.join(brands) or '-'}")
        return SaveSummary(0, 0, skipped + len(normalized), tuple(brands))

    if not supabase:
        print("[WARN] Supabase env values are missing. Nothing was written.")
        return SaveSummary(0, 0, skipped, ())

    stations_touched = 0
    brands_touched = set(brands)
    try:
        stations_touched = _bulk_write_station_inventory(normalized)
    except Exception as exc:
        skipped += len(normalized)
        brands_touched = set()
        print(f"[WARN] Station inventory bulk write failed: {exc}")

    print(f"[OK] {stations_touched} official station inventory rows processed. Skipped: {skipped}.")
    return SaveSummary(
        stations_touched=stations_touched,
        prices_touched=0,
        skipped_items=skipped,
        brands=tuple(sorted(brands_touched)),
    )
