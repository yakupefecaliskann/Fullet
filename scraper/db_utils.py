from __future__ import annotations

import os
import statistics
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
    normalize_province,
    split_province_district,
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
    _regional_targets_from_loaded,
    _chunks,
)

def _apply_sanity_gate_for_brands(
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], set[str]]:
    """Çapraz doğrulama kapısını marka bazında uygular.

    Bir koşuda birden fazla marka olabileceği için (nadiren) markalara ayrılıp
    her biri kendi referansına göre değerlendirilir.

    Döner: (filtrelenmiş öğeler, koşuda reddedilen yakıtların birleşimi).
    Birleşim kullanmak markalar arası kaba bir yaklaşımdır; pratikte her bot
    tek marka yazdığı için kayıp yoktur ve hata yönü GÜVENLİ taraftadır:
    fazladan muaf tutulan bir yakıt yalnızca "unknown'a düşürmeyi geciktirir",
    pg_cron zaten yaşa göre düşürür.
    """
    from sanity_gate import apply_sanity_gate

    by_brand: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_brand.setdefault(item["marka"], []).append(item)

    result: list[dict[str, Any]] = []
    rejected_fuels: set[str] = set()
    for brand, brand_items in by_brand.items():
        kept, rejected = apply_sanity_gate(brand_items, brand)
        result.extend(kept)
        rejected_fuels |= rejected
    return result, rejected_fuels


# Hedef bazlı kazıma yapan botlarda (şu an yalnızca shell_bot) bir koşunun
# "sağlıklı" sayılması için okunması gereken hedef oranı. Altına düşen koşu
# başarısız DEĞİL 'degraded' sayılır — gerekçe için bkz. finish_bot_run.
MIN_TARGET_COVERAGE = 0.70


def finish_bot_run(
    bot_name: str,
    *,
    scraped: int,
    summary: SaveSummary | None = None,
    targets_ok: int | None = None,
    targets_total: int | None = None,
) -> int:
    """Botun makine-okur kayıt satırını basar ve dürüst çıkış kodunu döner.

    run_all_bots.py stdout'taki [RECORDS] satırını parse edip bot_runs
    telemetrisine yazar. Scrape 0 kayıt döndürdüyse bot BAŞARISIZ sayılır
    (exit 1) — eski "boş liste + exit 0" kombinasyonu, kırık parser'ların
    aylarca 'success' görünmesine yol açıyordu (yol haritası S0-1). Yazılan
    kayıt sayısına (prices/stations) göre başarısızlık kararı VERİLMEZ:
    zero-cost diff nedeniyle değişmemiş fiyatlar meşru olarak 0 yazım üretir.

    --- Hedef kapsaması: Faz 0'ın kapatmadığı boşluk ---------------------------

    Faz 0 yalnızca "bot HİÇ kayıt üretmedi mi?" sorusunu görünür kıldı.
    "Bot hedeflerinin çoğunu kaybetti mi?" sorusu sorulmuyordu. shell_bot her
    koşuda 150 hedeften ~95'ini "Element is not visible" ile sessizce atlayıp
    yine de yüzlerce kayıt döndürüyor, dolayısıyla `success` görünüyordu.
    Sonuç canlıda ölçüldü: Shell'in 1.152 fiyat satırının yalnızca %26'sı
    taze, %36'sı bayat, %38'i bilinmiyor — diğer altı markada bayat SIFIR.

    Kapsama düşükse çıkış kodu 0 KALIR ve koşu 'degraded' işaretlenir.
    Gerekçe: 30 kapsamayla bile yazılan veri doğrudur ve değerlidir; exit 1
    dönmek 9 dakikalık kazımayı yeniden denetip aynı sonucu üretir ve
    pipeline'ı kalıcı kırmızıya boyar. 'degraded', "veri yazıldı ama eksik"
    durumunun kendi adıdır — 'success' yalanı ile 'failed' abartısı arasında.
    """
    stations = summary.stations_touched if summary else 0
    prices = summary.prices_touched if summary else 0
    records_line = f"[RECORDS] scraped={scraped} stations={stations} prices={prices}"
    if targets_total:
        records_line += f" targets_ok={targets_ok or 0} targets_total={targets_total}"
    print(records_line)

    if scraped == 0:
        print(
            f"[FAIL] {bot_name}: kaynak 0 kayıt döndürdü — "
            "parser kırık veya site erişilemez."
        )
        return 1

    if targets_total:
        coverage = (targets_ok or 0) / targets_total
        print(f"[COVERAGE] {bot_name}: {coverage:.0%} ({targets_ok}/{targets_total})")
        if coverage < MIN_TARGET_COVERAGE:
            print(
                f"[DEGRADED] {bot_name}: hedef kapsaması %{coverage * 100:.0f} "
                f"< %{MIN_TARGET_COVERAGE * 100:.0f} — veri yazıldı ama eksik."
            )
    return 0


def normalize_scraped_item(item: dict[str, Any], default_brand: str | None = None) -> dict[str, Any] | None:
    brand = normalize_brand(item.get("marka") or item.get("brand") or item.get("istasyon_adi"), default_brand)
    raw_city = item.get("il")
    city = normalize_province(raw_city)
    district = normalize_city(item.get("ilce"))
    # "İLÇE/İL" birleşik geldiyse ilçe tarafını da kurtar (ilce boşsa).
    if not district:
        _, embedded_district = split_province_district(raw_city)
        district = embedded_district
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
    raw_city = item.get("il") or item.get("city")
    city = normalize_province(raw_city)
    district = normalize_city(item.get("ilce") or item.get("district") or item.get("county"))
    if not district:
        _, district = split_province_district(raw_city)
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


def _apply_province_fallback_prices(
    *,
    normalized: list[dict[str, Any]],
    stations_by_brand_city: dict[tuple[str, str], list[dict[str, Any]]],
    station_updates_by_source: dict[str, set[str]],
    station_fuels: dict[str, set[str]],
    price_rows: list[dict[str, Any]],
    refreshed_at: str,
) -> None:
    """İlçesi beslemede olmayan istasyonlara il medyanı fiyatını yazar.

    --- Sorun (Faz 3 / F3-2) ---------------------------------------------
    Markalar iki farklı granülerlikte fiyat yayınlıyor:

      * Opet/PO/BP/Aytemiz -> İL düzeyinde (`ilce` boş). `_station_targets`'ın
        ilçe filtresi hiç devreye girmiyor, dolayısıyla o ildeki TÜM
        istasyonlar fiyat alıyor.
      * TotalEnergies/TP   -> İLÇE düzeyinde (`county_name`). Bu durumda
        `ilike("ilce", "%X%")` filtresi yalnızca beslemede ADI GEÇEN ilçeleri
        seçiyor; beslemenin kapsamadığı ilçelerdeki istasyonlar HİÇ fiyat
        almıyor.

    Canlı ölçüm: 140 aktif istasyon (TotalEnergies 132, TP 8) uygulamada
    görünür ama kalıcı olarak fiyatsızdı. 137'sinin `il` değeri markanın
    fiyatlı illeri arasındaydı — yani ili tutuyordu, onları kesen ilçe
    filtresiydi.

    --- Neden il medyanı güvenli? ----------------------------------------
    Ölçüldü (TotalEnergies canlı beslemesi, 944 satır): aynı il içinde
    ilçeler arası Motorin farkı **medyan 0,02 TL**, illerin 7'sinde tam
    sıfır. Tek anlamlı sapma K.MARAŞ (1,50 TL). Yani il düzeyinde tek fiyat
    kullanmak bu markalarda gerçeği neredeyse birebir yansıtıyor — üstelik
    diğer dört marka için sistem zaten TAM OLARAK bunu yapıyor.

    Bu bir tahmin üretmek değil, granülerlik farkını eşitlemektir: aksi hâlde
    aynı veri modelinde ilçe yayınlayan marka daha AZ istasyona ulaşıyor.
    """
    by_brand_city: dict[tuple[str, str], dict[str, list[float]]] = {}
    source_by_brand: dict[str, str] = {}
    for item in normalized:
        key = (item["marka"], item["il"])
        fuels = by_brand_city.setdefault(key, {})
        for fuel, price in item["fiyatlar"].items():
            fuels.setdefault(fuel, []).append(price)
        source_by_brand[item["marka"]] = item["veri_kaynagi"]

    filled_stations = 0
    filled_rows = 0
    for (brand, city), fuels in by_brand_city.items():
        stations = stations_by_brand_city.get((brand, city), [])
        if not stations:
            continue
        medians = {
            fuel: statistics.median(values)
            for fuel, values in fuels.items()
            if values
        }
        source = source_by_brand.get(brand, "")
        for station in stations:
            station_id = station["id"]
            already = station_fuels.get(station_id, set())
            missing = {f: p for f, p in medians.items() if f not in already}
            if not missing:
                continue
            filled_stations += 1
            station_updates_by_source.setdefault(source, set()).add(station_id)
            station_fuels.setdefault(station_id, set()).update(missing)
            for fuel, price in missing.items():
                filled_rows += 1
                price_rows.append({
                    "istasyon_id": station_id,
                    "yakit_tipi": fuel,
                    "fiyat": price,
                    "son_guncelleme": refreshed_at,
                    "veri_kaynagi": source,
                })

    if filled_stations:
        print(
            f"[IL-MEDYAN] {filled_stations} istasyona {filled_rows} fiyat il "
            "medyanından yazıldı (ilçesi beslemede yok)."
        )


def save_regional_prices_to_supabase(
    data: Iterable[dict[str, Any]],
    *,
    default_brand: str | None = None,
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
    normalized, rejected_fuels = _apply_sanity_gate_for_brands(normalized)
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

    _apply_province_fallback_prices(
        normalized=normalized,
        stations_by_brand_city=stations_by_brand_city,
        station_updates_by_source=station_updates_by_source,
        station_fuels=station_fuels,
        price_rows=price_rows,
        refreshed_at=refreshed_at,
    )

    for source, station_ids in station_updates_by_source.items():
        for batch in _chunks(sorted(station_ids), 500):
            supabase.table("istasyonlar").update({
                "veri_kaynagi": source,
                "aktif": True,
                "guncellenme_tarihi": refreshed_at,
            }).in_("id", batch).execute()

    prices_touched = _bulk_upsert_prices(price_rows)
    for fuel in CANONICAL_FUELS:
        # Kapının reddettiği yakıtı "raporlanmadı" sayma: reddetmek
        # "bu değere güvenmiyorum" demektir, "bu istasyonda bu yakıt yok"
        # demek değildir. Muaf tutulmazsa kapı, mevcut sağlam fiyatları
        # unknown'a çevirir — koruması gereken veriyi silerdi.
        if fuel in rejected_fuels:
            continue
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
    normalized, rejected_fuels = _apply_sanity_gate_for_brands(normalized)
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
        # bkz. save_regional_prices_to_supabase'deki aynı muafiyet.
        if fuel in rejected_fuels:
            continue
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
