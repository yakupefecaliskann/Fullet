from __future__ import annotations

import os
import sys
import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from dotenv import load_dotenv
from supabase import create_client

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / "database" / "add_status_columns.sql"
RPC_PATH = ROOT / "database" / "create_postgis_rpc.sql"
RLS_PATH = ROOT / "database" / "rls_policies.sql"
LIVE_FIX_PATH = ROOT / "database" / "live_public_schema_fix.sql"
NEWS_STALE_WARN_HOURS = 24
NEWS_STALE_FAIL_HOURS = 48
load_dotenv(ROOT / "scraper" / ".env")
load_dotenv(ROOT / "fullet_flutter" / ".env")


def _env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _ok(label: str, detail: str = "") -> None:
    print(f"[OK] {label}{': ' + detail if detail else ''}")


def _warn(label: str, detail: str = "") -> None:
    print(f"[WARN] {label}{': ' + detail if detail else ''}")


def _fail(label: str, detail: str = "") -> None:
    print(f"[FAIL] {label}{': ' + detail if detail else ''}")


def _migration_hint() -> str:
    return (
        f"run {MIGRATION_PATH}, then {RPC_PATH}, then {RLS_PATH}; "
        f"do not use legacy {LIVE_FIX_PATH.name} unless intentionally repairing an old schema"
    )


def _jwt_role(token: str | None) -> str | None:
    if not token or token.count(".") < 2:
        return None
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode("ascii"))
        claims = json.loads(decoded.decode("utf-8"))
    except Exception:
        return None
    return claims.get("role")


def _count(client, table: str) -> int:
    response = client.table(table).select("id", count="exact").limit(1).execute()
    return int(response.count or 0)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _select_all(client, table: str, select: str, page_size: int = 1000):
    rows = []
    start = 0
    while True:
        end = start + page_size - 1
        page = (
            client.table(table).select(select).order("id").range(start, end).execute().data or []
        )
        rows.extend(page)
        if len(page) < page_size:
            break
        start += page_size
    return rows


def main() -> int:
    url = _env("SUPABASE_URL")
    service_key = _env("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY", "SUPABASE_KEY")
    anon_key = _env("SUPABASE_ANON_KEY")

    if not url or not service_key:
        _fail("service env", "SUPABASE_URL or service key missing")
        return 1
    if not anon_key:
        _fail("anon env", "SUPABASE_ANON_KEY missing")
        return 1

    parsed = urlparse(url)
    _ok("supabase project", parsed.netloc or url)

    service_role = _jwt_role(service_key)
    anon_role = _jwt_role(anon_key)
    if service_role != "service_role":
        _fail("service key role", f"expected service_role, got {service_role or 'unknown'}")
        return 1
    _ok("service key role", "service_role")
    if anon_role != "anon":
        _fail("anon key role", f"expected anon, got {anon_role or 'unknown'}")
        return 1
    _ok("anon key role", "anon")

    service = create_client(url, service_key)
    anon = create_client(url, anon_key)

    failed = False

    for table in ("istasyonlar", "fiyatlar", "fiyat_gecmisi", "haberler"):
        try:
            count = _count(service, table)
            _ok(f"{table} service read", f"{count} rows")
        except Exception as exc:
            _fail(f"{table} service read", str(exc))
            failed = True

    try:
        latest_news = (
            service.table("haberler")
            .select("baslik,kaynak,tarih")
            .order("tarih", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        latest = latest_news[0] if latest_news else None
        latest_at = _parse_datetime(latest.get("tarih") if latest else None)
        if latest_at is None:
            _fail("news freshness", "latest haberler.tarih is missing or invalid")
            failed = True
        else:
            age_hours = (datetime.now(timezone.utc) - latest_at).total_seconds() / 3600
            detail = f"{age_hours:.1f}h old; {latest.get('kaynak')}: {latest.get('baslik')}"
            if age_hours > NEWS_STALE_FAIL_HOURS:
                _fail("news freshness", detail)
                failed = True
            elif age_hours > NEWS_STALE_WARN_HOURS:
                _warn("news freshness", detail)
            else:
                _ok("news freshness", detail)
    except Exception as exc:
        _fail("news freshness", str(exc))
        failed = True

    schema_checks = {
        "istasyonlar": "id,aktif,veri_kaynagi,guncellenme_tarihi,visibility_status",
        "fiyatlar": "id,veri_kaynagi,price_status",
        "push_tokens": "id,provider,son_guncelleme",
    }
    for table, select in schema_checks.items():
        try:
            service.table(table).select(select).limit(1).execute()
            _ok(f"{table} release columns", select)
        except Exception as exc:
            _fail(f"{table} release columns", f"{exc}; {_migration_hint()}")
            failed = True

    try:
        has_active_column = True
        try:
            stations = _select_all(service, "istasyonlar", "id,marka,isim,il,ilce,enlem,boylam,aktif,visibility_status")
        except Exception as exc:
            if "aktif" not in str(exc) and "visibility_status" not in str(exc):
                raise
            has_active_column = False
            _fail("schema istasyonlar.aktif/visibility_status", f"missing; {_migration_hint()}")
            stations = _select_all(service, "istasyonlar", "id,marka,isim,il,ilce,enlem,boylam")
            failed = True

        invalid_coords = [
            row for row in stations
            if (row.get("enlem") is None) != (row.get("boylam") is None)
            or (
                row.get("enlem") is not None
                and not (35 <= float(row["enlem"]) <= 43 and 25 <= float(row["boylam"]) <= 46)
            )
        ]
        empty_core = [row for row in stations if not row.get("marka") or not row.get("isim")]
        if invalid_coords:
            _fail("station coordinate quality", f"{len(invalid_coords)} invalid rows in sample")
            failed = True
        else:
            _ok("station coordinate quality", "sample clean")
        if empty_core:
            _fail("station required fields", f"{len(empty_core)} empty brand/name rows in sample")
            failed = True
        else:
            _ok("station required fields", "all checked rows clean")
        if has_active_column:
            inactive_visible_risk = [row for row in stations if row.get("aktif") is False]
            if inactive_visible_risk:
                _warn("inactive stations", f"{len(inactive_visible_risk)} inactive rows exist; RLS should hide them")
            hidden_risk = [row for row in stations if row.get("visibility_status") == "hidden" and row.get("aktif") is True]
            if hidden_risk:
                _warn("hidden but active stations", f"{len(hidden_risk)} rows are active but visibility_status is hidden")
    except Exception as exc:
        _fail("station quality check", str(exc))
        failed = True

    try:
        prices = _select_all(service, "fiyatlar", "id,istasyon_id,yakit_tipi,fiyat,son_guncelleme,price_status")
        invalid_prices = [
            row for row in prices
            if row.get("fiyat") is None
            or float(row["fiyat"]) < 5       # Yeni alt sınır: 5 TL (eski: 0)
            or float(row["fiyat"]) >= 200    # Yeni üst sınır: 200 TL (eski: 300)
            or row.get("yakit_tipi") not in ("Kursunsuz 95", "Motorin", "LPG")
        ]
        duplicate_keys = set()
        seen_keys = set()
        for row in prices:
            key = (row.get("istasyon_id"), row.get("yakit_tipi"))
            if key in seen_keys:
                duplicate_keys.add(key)
            seen_keys.add(key)
        if invalid_prices:
            _fail("fuel price quality", f"{len(invalid_prices)} invalid rows (fiyat<5 or >=200 or unknown fuel)")
            failed = True
        else:
            _ok("fuel price quality", "all checked rows clean (5 <= fiyat < 200)")
        if duplicate_keys:
            _fail("fuel price duplicates", f"{len(duplicate_keys)} duplicate keys")
            failed = True
        else:
            _ok("fuel price duplicates", "all checked rows clean")

        # price_status dağılımı
        status_counts: dict[str, int] = {}
        for row in prices:
            s = row.get("price_status") or "unknown"
            status_counts[s] = status_counts.get(s, 0) + 1
        status_summary = ", ".join(f"{k}:{v}" for k, v in sorted(status_counts.items()))
        stale_ratio = (status_counts.get("stale", 0) + status_counts.get("unknown", 0)) / max(len(prices), 1)
        if stale_ratio > 0.5:
            _warn("price freshness ratio", f">{int(stale_ratio*100)}% stale/unknown — {status_summary}")
        else:
            _ok("price freshness ratio", status_summary)
    except Exception as exc:
        _fail("price quality check", str(exc))
        failed = True

    try:
        rpc = service.rpc("get_nearby_stations", {
            "lat": 41.0082,
            "lng": 28.9784,
            "max_dist_meters": 20000,
            "max_results": 50,
        }).execute()
        _ok("RPC get_nearby_stations v1", f"{len(rpc.data or [])} rows")
    except Exception as exc:
        _warn("RPC new signature", f"{exc}")
        try:
            rpc = service.rpc("get_nearby_stations", {
                "lat": 41.0082,
                "lng": 28.9784,
                "max_dist_meters": 20000,
            }).execute()
            _warn("RPC legacy signature still active", f"{len(rpc.data or [])} rows; {_migration_hint()}")
            failed = True
        except Exception as legacy_exc:
            _fail("RPC get_nearby_stations", str(legacy_exc))
            failed = True

    # v2 RPC kontrolü (istasyon + fiyat birleşik sorgu)
    try:
        rpc_v2 = service.rpc("get_nearby_stations_v2", {
            "lat": 41.0082,
            "lng": 28.9784,
            "max_dist_meters": 20000,
            "max_results": 50,
        }).execute()
        rows_v2 = rpc_v2.data or []
        with_prices = sum(1 for r in rows_v2 if r.get("prices") and r["prices"] != {})
        _ok("RPC get_nearby_stations_v2", f"{len(rows_v2)} stations, {with_prices} with prices")
    except Exception as exc:
        _warn("RPC get_nearby_stations_v2", f"not yet deployed — run database/create_postgis_rpc.sql: {exc}")

    try:
        anon.table("istasyonlar").select("id").limit(1).execute()
        anon.table("fiyatlar").select("id").limit(1).execute()
        anon.table("haberler").select("id").limit(1).execute()
        _ok("anon public reads", "istasyonlar/fiyatlar/haberler")
    except Exception as exc:
        _fail("anon public reads", str(exc))
        failed = True

    try:
        inactive_rows = (
            anon.table("istasyonlar")
            .select("id,aktif")
            .eq("aktif", False)
            .limit(1)
            .execute()
            .data
            or []
        )
        if inactive_rows:
            _fail("anon inactive station visibility", f"inactive rows are public; {_migration_hint()}")
            failed = True
        else:
            _ok("anon inactive station visibility", "hidden by RLS")
    except Exception as exc:
        _fail("anon inactive station visibility", str(exc))
        failed = True

    test_name = f"RLS_TEST_{uuid4()}"
    inserted_id = None
    try:
        response = anon.table("istasyonlar").insert({
            "marka": "RLS_TEST",
            "isim": test_name,
            "il": "ISTANBUL",
            "ilce": "TEST",
        }).execute()
        if response.data:
            inserted_id = response.data[0].get("id")
            _fail("anon station write blocked", "anon insert unexpectedly succeeded")
            failed = True
        else:
            _ok("anon station write blocked")
    except Exception:
        _ok("anon station write blocked")
    finally:
        if inserted_id:
            service.table("istasyonlar").delete().eq("id", inserted_id).execute()
            _warn("anon write cleanup", inserted_id)

    if failed:
        _fail("backend health", "not perfect yet")
        return 1

    _ok("backend health", "all checked items passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
