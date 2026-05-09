from __future__ import annotations

import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
from dotenv import load_dotenv
from supabase import Client, create_client

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

SCRAPER_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRAPER_DIR.parent
load_dotenv(SCRAPER_DIR / ".env")
load_dotenv(PROJECT_DIR / ".env")

CANONICAL_FUELS = ("Kursunsuz 95", "Motorin", "LPG")
VALID_BRANDS = {
    "Shell",
    "Opet",
    "Petrol Ofisi",
    "BP",
    "Aytemiz",
    "TotalEnergies",
    "Türkiye Petrolleri",
}

OFFICIAL_REGIONAL_SOURCES = {
    "api.opet.com.tr/api/fuelprices/allprices",
    "petrolofisi.com.tr/akaryakit-fiyatlari",
    "petrolofisi.com.tr/akaryakit-fiyatlari-bp",
    "aytemiz.com.tr/akaryakit-fiyatlari",
    "turkiyeshell.com/pompatest/History.aspx",
    "apimobile.guzelenerji.com.tr/exapi/fuel_prices",
    "www.tppd.com.tr/akaryakit-fiyatlari",
}

OFFICIAL_STATION_SOURCES = {
    "apimobile.guzelenerji.com.tr/exapi/stations",
    "www.tppd.com.tr/tr/stationmaplist",
    "find.shell.com/tr/fuel",
}

BRAND_ALIASES = {
    "SHELL": "Shell",
    "OPET": "Opet",
    "PETROL OFISI": "Petrol Ofisi",
    "PETROL OFİSİ": "Petrol Ofisi",
    "PO": "Petrol Ofisi",
    "BP": "BP",
    "TOTAL": "TotalEnergies",
    "TOTALENERGIES": "TotalEnergies",
    "TOTAL ENERGIES": "TotalEnergies",
    "AYTEMIZ": "Aytemiz",
    "AYTEMİZ": "Aytemiz",
    "TP": "Türkiye Petrolleri",
    "TPPD": "Türkiye Petrolleri",
    "TURKIYE PETROLLERI": "Türkiye Petrolleri",
    "TÜRKİYE PETROLLERİ": "Türkiye Petrolleri",
    "TURKIYE PETROL": "Türkiye Petrolleri",
}

CITY_REPLACEMENTS = str.maketrans({
    "İ": "I",
    "I": "I",
    "ı": "I",
    "Ş": "S",
    "ş": "S",
    "Ç": "C",
    "ç": "C",
    "Ğ": "G",
    "ğ": "G",
    "Ü": "U",
    "ü": "U",
    "Ö": "O",
    "ö": "O",
})

ISTANBUL_REGION_DISTRICTS = {
    "ANADOLU": {
        "ADALAR",
        "ATASEHIR",
        "BEYKOZ",
        "CEKMEKOY",
        "KADIKOY",
        "KARTAL",
        "MALTEPE",
        "PENDIK",
        "SANCAKTEPE",
        "SILE",
        "SULTANBEYLI",
        "TUZLA",
        "UMRANIYE",
        "USKUDAR",
    },
    "AVRUPA": {
        "ARNAVUTKOY",
        "AVCILAR",
        "BAGCILAR",
        "BAHCELIEVLER",
        "BAKIRKOY",
        "BASAKSEHIR",
        "BAYRAMPASA",
        "BESIKTAS",
        "BEYLIKDUZU",
        "BEYOGLU",
        "BUYUKCEKMECE",
        "CATALCA",
        "ESENLER",
        "ESENYURT",
        "EYUP",
        "EYUPSULTAN",
        "FATIH",
        "GAZIOSMANPASA",
        "GUNGOREN",
        "KAGITHANE",
        "KUCUKCEKMECE",
        "SARIYER",
        "SILIVRI",
        "SULTANGAZI",
        "SISLI",
        "ZEYTINBURNU",
    },
}


@dataclass(frozen=True)
class SaveSummary:
    stations_touched: int = 0
    prices_touched: int = 0
    skipped_items: int = 0
    brands: tuple[str, ...] = ()


def _get_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


SUPABASE_URL = _get_env("SUPABASE_URL")
SUPABASE_KEY = _get_env("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY", "SUPABASE_KEY")

try:
    supabase: Client | None = (
        create_client(SUPABASE_URL, SUPABASE_KEY)
        if SUPABASE_URL and SUPABASE_KEY
        else None
    )
except Exception as exc:
    print(f"[WARN] Supabase client could not be created: {exc}")
    supabase = None


def _compact_log(value: Any, limit: int = 4000) -> str:
    text = clean_text(value)
    if len(text) <= limit:
        return text
    return text[:limit - 3] + "..."


def _observability_table_missing(exc: Exception) -> bool:
    text = str(exc)
    return (
        "system_alerts" in text
        or "bot_runs" in text
        or "Could not find the table" in text
        or "relation" in text and "does not exist" in text
        or "PGRST205" in text
    )


def record_bot_run(
    *,
    bot_name: str,
    mode: str | None,
    status: str,
    started_at: datetime,
    finished_at: datetime | None,
    duration_seconds: float | None = None,
    exit_code: int | None = None,
    summary: str | None = None,
    stdout: str | None = None,
    stderr: str | None = None,
) -> None:
    if not supabase:
        return
    try:
        supabase.table("bot_runs").insert({
            "bot_name": clean_text(bot_name),
            "mode": clean_text(mode),
            "status": status,
            "started_at": started_at.astimezone(timezone.utc).isoformat(),
            "finished_at": finished_at.astimezone(timezone.utc).isoformat() if finished_at else None,
            "duration_seconds": round(duration_seconds, 2) if duration_seconds is not None else None,
            "exit_code": exit_code,
            "summary": _compact_log(summary or "", 500),
            "stdout_excerpt": _compact_log(stdout or ""),
            "stderr_excerpt": _compact_log(stderr or ""),
        }).execute()
    except Exception as exc:
        if not _observability_table_missing(exc):
            print(f"[WARN] Bot run telemetry skipped: {exc}")


def create_system_alert(
    *,
    severity: str,
    source: str,
    title: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    if not supabase:
        return
    severity = severity if severity in {"info", "warning", "error", "critical"} else "warning"
    source = clean_text(source)[:120]
    title = clean_text(title)[:160]
    payload = {
        "severity": severity,
        "source": source,
        "title": title,
        "message": _compact_log(message, 2000),
        "status": "open",
        "metadata": metadata or {},
    }
    try:
        existing = (
            supabase.table("system_alerts")
            .select("id")
            .eq("source", source)
            .eq("title", title)
            .eq("status", "open")
            .limit(1)
            .execute()
            .data
            or []
        )
        if existing:
            supabase.table("system_alerts").update(payload).eq("id", existing[0]["id"]).execute()
        else:
            supabase.table("system_alerts").insert(payload).execute()
    except Exception as exc:
        if not _observability_table_missing(exc):
            print(f"[WARN] System alert skipped: {exc}")


def resolve_system_alerts(*, source: str, title: str | None = None) -> None:
    if not supabase:
        return
    try:
        query = (
            supabase.table("system_alerts")
            .update({
                "status": "resolved",
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("source", clean_text(source)[:120])
            .eq("status", "open")
        )
        if title:
            query = query.eq("title", clean_text(title)[:160])
        query.execute()
    except Exception as exc:
        if not _observability_table_missing(exc):
            print(f"[WARN] System alert resolve skipped: {exc}")


def is_dry_run() -> bool:
    return os.environ.get("FULLET_DRY_RUN", "0") == "1"


def is_write_allowed() -> bool:
    return os.environ.get("FULLET_ALLOW_DB_WRITE", "0") == "1"


def allow_inferred_data() -> bool:
    return os.environ.get("FULLET_ALLOW_INFERRED_DATA", "0") == "1"


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_city(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""
    text = text.translate(CITY_REPLACEMENTS).upper()
    text = text.replace("ISTANBUL ANADOLU", "ISTANBUL")
    text = text.replace("ISTANBUL AVRUPA", "ISTANBUL")
    text = text.replace("(AVRUPA)", "")
    text = text.replace("(ANADOLU)", "")
    text = text.replace("ISTANBUL / ANADOLU", "ISTANBUL")
    text = text.replace("ISTANBUL / AVRUPA", "ISTANBUL")
    text = text.replace("İSTANBUL", "ISTANBUL")
    text = clean_text(text)
    city_aliases = {
        "AFYON": "AFYONKARAHISAR",
        "K.MARAS": "KAHRAMANMARAS",
        "KAHRAMANMARAŞ": "KAHRAMANMARAS",
        "ICEL": "MERSIN",
        "İÇEL": "MERSIN",
    }
    return city_aliases.get(text, text)


def istanbul_region_from_city(value: Any) -> str:
    text = clean_text(value).translate(CITY_REPLACEMENTS).upper()
    if "ISTANBUL" not in text:
        return ""
    if "ANADOLU" in text:
        return "ANADOLU"
    if "AVRUPA" in text:
        return "AVRUPA"
    return ""


def _station_district_in_istanbul_region(district: Any, region: str) -> bool:
    normalized = normalize_city(district)
    return normalized in ISTANBUL_REGION_DISTRICTS.get(region, set())


def normalize_brand(value: Any, default_brand: str | None = None) -> str | None:
    candidates = [clean_text(value), clean_text(default_brand)]
    for candidate in candidates:
        if not candidate:
            continue
        upper = candidate.translate(CITY_REPLACEMENTS).upper()
        for alias, brand in BRAND_ALIASES.items():
            if upper == alias or upper.startswith(f"{alias} ") or f" {alias} " in f" {upper} ":
                return brand
    return default_brand if default_brand in VALID_BRANDS else None


def normalize_fuel(value: Any) -> str | None:
    text = clean_text(value).lower()
    if not text:
        return None
    if "kursunsuz" in text or "benzin" in text or "95" in text:
        return "Kursunsuz 95"
    if "motorin" in text or "dizel" in text or "mazot" in text:
        return "Motorin"
    if "lpg" in text or "oto gaz" in text or "otogaz" in text:
        return "LPG"
    return None


def parse_price(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        price = float(value)
        return round(price, 2) if 0 < price < 300 else None

    text = clean_text(value)
    if not text or text == "-":
        return None
    text = re.sub(r"[^0-9,.\-]", "", text)
    if not text or text == "-":
        return None

    has_comma = "," in text
    has_dot = "." in text
    if has_comma and has_dot:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif has_comma:
        text = text.replace(",", ".")

    try:
        price = float(text)
    except ValueError:
        return None
    return round(price, 2) if 0 < price < 300 else None


def parse_coordinate(value: Any, *, latitude: bool) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        coord = float(value)
    else:
        text = clean_text(value)
        if not text or text == "-":
            return None
        text = re.sub(r"[^0-9,.\-]", "", text)
        if not text or text == "-":
            return None

        has_comma = "," in text
        has_dot = "." in text
        if has_comma and has_dot:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif has_comma:
            text = text.replace(",", ".")

        try:
            coord = float(text)
        except ValueError:
            return None

    if latitude and 35 <= coord <= 43:
        return round(coord, 6)
    if not latitude and 25 <= coord <= 46:
        return round(coord, 6)
    return None


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


def _chunks(items: list[Any], size: int = 100) -> Iterable[list[Any]]:
    for index in range(0, len(items), size):
        yield items[index:index + size]


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
            for batch in _chunks(station_ids):
                supabase.table("istasyonlar").update({
                    "veri_kaynagi": item["veri_kaynagi"],
                    "aktif": True,
                    "guncellenme_tarihi": datetime.now(timezone.utc).isoformat(),
                }).in_("id", batch).execute()
        return targets

    existing = (
        supabase.table("istasyonlar")
        .select("id,enlem,boylam")
        .eq("marka", brand)
        .eq("isim", item["isim"])
        .limit(1)
        .execute()
    )
    if existing.data:
        station_id = existing.data[0]["id"]
        supabase.table("istasyonlar").update({
            "il": city,
            "ilce": district,
            "adres": item.get("adres"),
            "enlem": item["enlem"],
            "boylam": item["boylam"],
            "veri_kaynagi": item["veri_kaynagi"],
            "aktif": True,
            "guncellenme_tarihi": datetime.now(timezone.utc).isoformat(),
        }).eq("id", station_id).execute()
        return [{"id": station_id}]

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
            "guncellenme_tarihi": datetime.now(timezone.utc).isoformat(),
    }).execute()
    return [{"id": inserted.data[0]["id"]}]


def _bulk_upsert_prices(rows: list[dict[str, Any]]) -> int:
    assert supabase is not None
    if not rows:
        return 0
    deduped_rows = {
        (row["istasyon_id"], row["yakit_tipi"]): row
        for row in rows
    }
    rows = list(deduped_rows.values())
    try:
        for batch in _chunks(rows, 500):
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
            for row in rows
        ]
        for batch in _chunks(fallback_rows, 500):
            supabase.table("fiyatlar").upsert(
                batch,
                on_conflict="istasyon_id,yakit_tipi",
            ).execute()
    return len(rows)


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
        round(latitude, 6),
        round(longitude, 6),
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
            updates.append({"id": station_id, **payload})
        else:
            inserts.append({
                **payload,
                "aktif": False,
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


def _delete_unreported_prices(station_ids: list[str], fuels: set[str]) -> int:
    assert supabase is not None
    deleted = 0
    if not station_ids:
        return deleted
    for fuel in CANONICAL_FUELS:
        if fuel in fuels:
            continue
        for batch in _chunks(station_ids, 200):
            try:
                response = (
                    supabase.table("fiyatlar")
                    .delete()
                    .in_("istasyon_id", batch)
                    .eq("yakit_tipi", fuel)
                    .execute()
                )
                deleted += len(response.data or [])
            except Exception as exc:
                print(f"[WARN] stale price cleanup failed for {fuel}: {exc}")
    return deleted


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
            station_fuels[station_id] = fuels
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
                    .delete()
                    .in_("istasyon_id", batch)
                    .eq("yakit_tipi", fuel)
                    .execute()
                )
                prices_touched += len(response.data or [])
            except Exception as exc:
                print(f"[WARN] stale price cleanup failed for {fuel}: {exc}")

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

    stations_touched = 0
    prices_touched = 0
    brands_touched: set[str] = set()

    _reset_split_region_targets(normalized)

    for item in normalized:
        try:
            targets = _station_targets(item)
            station_ids = [target["id"] for target in targets]
            refreshed_at = datetime.now(timezone.utc).isoformat()
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
            prices_touched += _delete_unreported_prices(station_ids, set(item["fiyatlar"]))
            stations_touched += len(station_ids)
            if station_ids:
                brands_touched.add(item["marka"])
        except Exception as exc:
            skipped += 1
            print(f"[WARN] DB write skipped for {item.get('marka')} {item.get('il')} {item.get('ilce')}: {exc}")

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
