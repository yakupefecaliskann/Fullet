from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Iterable

import requests

from config import supabase, SUPABASE_URL, SUPABASE_KEY, CANONICAL_FUELS, ISTANBUL_REGION_DISTRICTS, is_write_allowed, is_dry_run
from freshness import needs_verification_write, now_utc
from matching import (
    StationProximityIndex,
    _existing_station_inventory_indexes,
    _regional_targets_from_loaded,
    _station_inventory_key,
    _station_targets,
    station_coordinates,
)
from normalization import (
    clean_text,
    normalize_city,
    normalize_province,
    split_province_district,
)
from models import SaveSummary

def _chunks(items: list[Any], size: int = 100) -> Iterable[list[Any]]:
    for index in range(0, len(items), size):
        yield items[index:index + size]

def _bulk_upsert_prices(rows: list[dict[str, Any]]) -> int:
    """Fiyatları yazar ve doğrulama izini (`son_dogrulama`) günceller.

    İki ayrı yazma yolu vardır — bu ayrım `son_guncelleme` semantiğini korur:

      * **Değişen/yeni fiyat** -> tam upsert. `son_guncelleme` ilerler
        (trigger `log_fiyat_degisimi` fiyat_gecmisi'ne kayıt düşer).
      * **Değişmemiş fiyat** -> yalnızca `son_dogrulama` + `price_status`
        güncellenir. `fiyat` alanına dokunulmadığı için trigger tetiklenmez ve
        "son değişim zamanı" bozulmaz.

    Eski kod değişmemiş fiyatları TAMAMEN atlıyordu (veya 24 saati aşınca
    `son_guncelleme`'yi sahte biçimde ilerletiyordu). Atlanan satır "bu fiyatı
    bugün doğruladık" bilgisini kaybettiriyor, 12 saatlik pg_cron eşiği de
    doğru fiyatı bayat işaretliyordu (bkz. freshness.py).
    """
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
                .select(
                    "istasyon_id, yakit_tipi, fiyat, price_status, "
                    "son_guncelleme, son_dogrulama"
                )
                .in_("istasyon_id", batch)
                .execute()
            )
            for r in (res.data or []):
                existing_prices[(r["istasyon_id"], r["yakit_tipi"])] = r
        except Exception as exc:
            print(f"[WARN] Failed to fetch existing prices for diffing: {exc}")

    reference = now_utc()
    verified_at = reference.isoformat()
    rows_to_upsert: list[dict[str, Any]] = []
    # (yakit_tipi -> istasyon_id listesi): fiyatı değişmemiş, yalnızca
    # doğrulama izi güncellenecek satırlar.
    confirm_by_fuel: dict[str, list[str]] = {}

    for row in unique_rows:
        key = (row["istasyon_id"], row["yakit_tipi"])
        existing = existing_prices.get(key)
        row["son_dogrulama"] = verified_at

        if not existing:
            row["price_status"] = "fresh"
            rows_to_upsert.append(row)
            continue

        price_changed = float(existing.get("fiyat", 0)) != float(row.get("fiyat", 0))
        if price_changed:
            row["price_status"] = "fresh"
            rows_to_upsert.append(row)
            continue

        # Fiyat aynı: tam satır yazmaya gerek yok, doğrulama izi yeterli.
        if needs_verification_write(
            existing.get("son_dogrulama") or existing.get("son_guncelleme"),
            existing.get("price_status"),
            reference=reference,
        ):
            confirm_by_fuel.setdefault(row["yakit_tipi"], []).append(row["istasyon_id"])

    written = _write_price_rows(rows_to_upsert)
    written += _confirm_unchanged_prices(confirm_by_fuel, verified_at)
    return written


def _write_price_rows(rows_to_upsert: list[dict[str, Any]]) -> int:
    if not rows_to_upsert:
        return 0

    def _upsert(batch_rows: list[dict[str, Any]]) -> None:
        for batch in _chunks(batch_rows, 500):
            supabase.table("fiyatlar").upsert(
                batch,
                on_conflict="istasyon_id,yakit_tipi",
            ).execute()

    try:
        _upsert(rows_to_upsert)
    except Exception as exc:
        message = str(exc)
        missing = next(
            (col for col in ("veri_kaynagi", "son_dogrulama") if col in message),
            None,
        )
        if missing is None:
            raise
        print(
            f"[WARN] fiyatlar.{missing} kolonu yok; "
            "database/add_price_verification.sql (ve production_hardening.sql) çalıştırılmalı."
        )
        fallback_rows = [
            {key: value for key, value in row.items() if key != missing}
            for row in rows_to_upsert
        ]
        _upsert(fallback_rows)

    return len(rows_to_upsert)


def _confirm_unchanged_prices(
    confirm_by_fuel: dict[str, list[str]],
    verified_at: str,
) -> int:
    """Fiyatı değişmemiş satırlarda yalnızca doğrulama izini günceller.

    `fiyat` yazılmadığı için `log_fiyat_degisimi` trigger'ı tetiklenmez —
    fiyat_gecmisi'ne sahte değişim kaydı düşmez ve `son_guncelleme` korunur.
    """
    confirmed = 0
    for fuel, station_ids in confirm_by_fuel.items():
        for batch in _chunks(sorted(set(station_ids)), 500):
            try:
                supabase.table("fiyatlar").update({
                    "son_dogrulama": verified_at,
                    "price_status": "fresh",
                }).in_("istasyon_id", batch).eq("yakit_tipi", fuel).execute()
                confirmed += len(batch)
            except Exception as exc:
                if "son_dogrulama" in str(exc):
                    print(
                        "[WARN] fiyatlar.son_dogrulama kolonu yok; "
                        "database/add_price_verification.sql çalıştırılmalı."
                    )
                    return confirmed
                print(f"[WARN] {fuel} doğrulama izi güncellenemedi: {exc}")
    return confirmed

def _bulk_write_station_inventory(items: list[dict[str, Any]]) -> int:
    assert supabase is not None
    if not items:
        return 0

    # Girdideki BİREBİR aynı kayıtları teke indirir. Yakın-ama-aynı-değil
    # koordinatlar burada KASTEN elenmez; onları aşağıdaki yakınlık
    # eşleştirmesi (mevcut kayıtlara karşı) ve `batch_proximity` (parti içi)
    # çözer. Burada yuvarlanmış kova kullanmak, 11 m'lik kova sınırına düşen
    # gerçek istasyonları sessizce yutardı.
    deduped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in items:
        coordinates = station_coordinates(item)
        dedupe_key = (
            (clean_text(item["marka"]), *coordinates)
            if coordinates is not None
            else _station_inventory_key(item)
        )
        deduped[dedupe_key] = item

    now = datetime.now(timezone.utc).isoformat()
    existing_by_key, existing_proximity = _existing_station_inventory_indexes(
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
        coordinates = station_coordinates(item)
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
        if station_id is None and coordinates is not None:
            # Yakınlık eşleştirmesi: aynı marka + <=75 m => aynı istasyon.
            # İdari alanlar (il/ilce) kimliğe DAHİL DEĞİL — güvenilmezler ve
            # ilce='' vs ilce='ÇEKMEKÖY' farkı tek başına kopya üretiyordu.
            station_id = existing_proximity.find(
                item["marka"], coordinates[0], coordinates[1]
            )
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

    # Partinin KENDİ içindeki kopyalar. Burada da eskiden yuvarlanmış koordinat
    # anahtarı kullanılıyordu; aynı kova hatası aynı koşuda iki satır olarak
    # geri geliyordu. Artık aynı yakınlık kuralı uygulanıyor.
    batch_proximity = StationProximityIndex()
    deduped_inserts: list[dict[str, Any]] = []
    inserts_without_coord: list[dict[str, Any]] = []
    for row in inserts:
        coordinates = station_coordinates(row)
        if coordinates is None:
            inserts_without_coord.append(row)
            continue
        if batch_proximity.find(row["marka"], coordinates[0], coordinates[1]):
            continue
        index_position = str(len(deduped_inserts))
        batch_proximity.add(row["marka"], coordinates[0], coordinates[1], index_position)
        deduped_inserts.append(row)

    unique_updates = list(updates_by_id.values())
    unique_inserts = deduped_inserts + inserts_without_coord

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
    # item["ilce"] bu satırlarda gerçek bir ilçe adı değil, bölge etiketi
    # taşır ("ANADOLU"/"AVRUPA" — bkz. db_utils.normalize_scraped_item /
    # istanbul_region_from_city). ISTANBUL_REGION_DISTRICTS'in anahtarları
    # da tam olarak bu iki etiket, bu yüzden "tam kapsam" kontrolü gerçek
    # ilçe listesine karşı değil, bu iki etikete karşı yapılmalı.
    reset_groups: dict[tuple[str, str], set[str]] = {}
    for item in items:
        if (
            item.get("veri_kapsami") == "regional_official"
            and item.get("il") == "ISTANBUL"
            and item.get("ilce") in ISTANBUL_REGION_DISTRICTS
        ):
            reset_groups.setdefault((item["marka"], item["il"]), set()).add(item["ilce"])

    expected_regions = set(ISTANBUL_REGION_DISTRICTS.keys())  # {"ANADOLU", "AVRUPA"}

    for (brand, city), seen_regions in sorted(reset_groups.items()):
        if seen_regions != expected_regions:
            missing = sorted(expected_regions - seen_regions)
            print(
                f"[WARN] {brand} {city} split-region kazıma eksik "
                f"(bu run'da gelen bölgeler: {sorted(seen_regions)}, eksik: {missing}) "
                f"— toplu gizleme ATLANDI (yarım veriyle istasyon gizlemek daha riskli)."
            )
            continue
        try:
            supabase.table("istasyonlar").update({
                "aktif": False,
                "guncellenme_tarihi": datetime.now(timezone.utc).isoformat(),
            }).eq("marka", brand).eq("il", city).not_.ilike(
                "isim", "%Fullet Verisi%"
            ).execute()
            print(f"[INFO] Reset {brand} {city} (tam kapsam doğrulandı: {sorted(seen_regions)}).")
        except Exception as exc:
            print(
                f"[WARN] Reset {brand} {city} başarısız oldu: {exc} — istasyonlar "
                "gizlenmedi (hata durumunda gizleme yapılmaz)."
            )

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
                # DB'de "İLÇE/İL" birleşik yazılmış satırlar var; il tarafını
                # ayıklamazsak bu istasyonlar hiçbir bölgesel eşleşmeye
                # girmez (canlı: 20 satır, 0 taze fiyat).
                normalized_city = normalize_province(row.get("il"))
                normalized_district = normalize_city(row.get("ilce"))
                if not normalized_district:
                    _, normalized_district = split_province_district(row.get("il"))
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
