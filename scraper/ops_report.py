from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime, timezone

from db_utils import (
    OFFICIAL_REGIONAL_SOURCES,
    OFFICIAL_STATION_SOURCES,
    create_system_alert,
    normalize_brand,
    resolve_system_alerts,
    supabase,
)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

BRANDS = [
    "Shell",
    "TotalEnergies",
    normalize_brand("TP"),
    "Opet",
    "Petrol Ofisi",
    "BP",
    "Aytemiz",
]

# Conservative release gates. These are intentionally below the current live
# counts, so normal day-to-day source movement will pass but a broken parser or
# partial bot run will stop the release check.
MIN_ACTIVE_STATIONS = {
    "Shell": 500,
    "TotalEnergies": 500,
    normalize_brand("TP"): 30,
    "Opet": 400,
    "Petrol Ofisi": 50,
    "BP": 30,
    "Aytemiz": 25,
}

MIN_PRICE_ROWS = {
    "Shell": 1500,
    "TotalEnergies": 900,
    normalize_brand("TP"): 60,
    "Opet": 800,
    "Petrol Ofisi": 150,
    "BP": 80,
    "Aytemiz": 50,
}

MAX_PRICE_AGE_HOURS = 48
VERIFIED_SOURCES = OFFICIAL_REGIONAL_SOURCES | OFFICIAL_STATION_SOURCES


def _chunks(items, size=200):
    for index in range(0, len(items), size):
        yield items[index:index + size]


def _select_brand_stations(brand):
    assert supabase is not None
    rows = []
    start = 0
    while True:
        page = (
            supabase.table("istasyonlar")
            .select("id,marka,il,aktif,veri_kaynagi,guncellenme_tarihi")
            .eq("marka", brand)
            .range(start, start + 999)
            .execute()
            .data
            or []
        )
        rows.extend(page)
        if len(page) < 1000:
            break
        start += 1000
    return rows


def _select_prices(station_ids):
    assert supabase is not None
    prices = []
    for batch in _chunks(station_ids):
        prices.extend(
            supabase.table("fiyatlar")
            .select("istasyon_id,yakit_tipi,fiyat,son_guncelleme")
            .in_("istasyon_id", batch)
            .execute()
            .data
            or []
        )
    return prices


def _parse_datetime(value):
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_hours(value):
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    return (datetime.now(timezone.utc) - parsed).total_seconds() / 3600


def _age_text(value):
    hours = _age_hours(value)
    if hours is None:
        return "-"
    whole_hours = int(hours)
    if whole_hours < 1:
        return "<1h"
    if whole_hours < 24:
        return f"{whole_hours}h"
    return f"{whole_hours // 24}d"


def main() -> int:
    if supabase is None:
        print("[FAIL] Supabase env values are missing.")
        return 1

    print("Fullet live data report")
    print("=" * 72)
    print(
        f"{'Brand':<20} {'Active':>6} {'Total':>6} {'Prices':>7} "
        f"{'City':>4} {'Fuels':<26} {'Latest':>7}"
    )
    print("-" * 72)

    total_active = 0
    total_prices = 0
    warnings = []

    for brand in BRANDS:
        stations = _select_brand_stations(brand)
        active = [row for row in stations if row.get("aktif") is True]
        prices = _select_prices([row["id"] for row in active])
        fuels = Counter(row.get("yakit_tipi") for row in prices)
        latest = max(
            [row.get("son_guncelleme") for row in prices if row.get("son_guncelleme")],
            default=None,
        )
        active_cities = len({row.get("il") for row in active if row.get("il")})
        total_active += len(active)
        total_prices += len(prices)

        if not active:
            warnings.append(f"{brand}: no active stations")
        if latest is None:
            warnings.append(f"{brand}: no price update timestamp")
        if len(active) < MIN_ACTIVE_STATIONS.get(brand, 1):
            warnings.append(
                f"{brand}: active station count too low "
                f"({len(active)} < {MIN_ACTIVE_STATIONS[brand]})"
            )
        if len(prices) < MIN_PRICE_ROWS.get(brand, 1):
            warnings.append(
                f"{brand}: price row count too low ({len(prices)} < {MIN_PRICE_ROWS[brand]})"
            )
        latest_age = _age_hours(latest)
        if latest_age is not None and latest_age > MAX_PRICE_AGE_HOURS:
            warnings.append(
                f"{brand}: stale price data ({_age_text(latest)} > {MAX_PRICE_AGE_HOURS}h)"
            )
        unverified_sources = sorted({
            row.get("veri_kaynagi") or ""
            for row in active
            if (row.get("veri_kaynagi") or "") not in VERIFIED_SOURCES
        })
        if unverified_sources:
            preview = ", ".join(source or "(empty)" for source in unverified_sources[:3])
            warnings.append(f"{brand}: unverified active station source ({preview})")

        fuel_text = ", ".join(
            f"{fuel}:{count}"
            for fuel, count in sorted(fuels.items())
            if fuel
        )
        print(
            f"{brand:<20} {len(active):>6} {len(stations):>6} {len(prices):>7} "
            f"{active_cities:>4} {fuel_text[:26]:<26} {_age_text(latest):>7}"
        )

    print("-" * 72)
    print(f"Total active stations: {total_active}")
    print(f"Total active prices: {total_prices}")

    if warnings:
        print("\nWarnings")
        for warning in warnings:
            print(f"[WARN] {warning}")
            create_system_alert(
                severity="warning",
                source="ops_report",
                title=warning.split(":", 1)[0],
                message=warning,
                metadata={"report": "live_data"},
            )
        return 1

    resolve_system_alerts(source="ops_report")
    print("\n[OK] Live data operations report is clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
