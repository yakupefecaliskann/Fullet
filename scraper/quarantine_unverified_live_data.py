from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

from db_utils import OFFICIAL_REGIONAL_SOURCES, OFFICIAL_STATION_SOURCES

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "scraper" / ".env")

OFFICIAL_SOURCES = OFFICIAL_REGIONAL_SOURCES | OFFICIAL_STATION_SOURCES


def _env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _chunks(items: list[str], size: int = 100):
    for index in range(0, len(items), size):
        yield items[index:index + size]


def _is_verified_station(row: dict) -> bool:
    source = row.get("veri_kaynagi") or ""
    name = row.get("isim") or ""
    return (
        source in OFFICIAL_SOURCES
        and "Fullet Verisi" not in name
        and row.get("enlem") is not None
        and row.get("boylam") is not None
    )


def main() -> int:
    if os.environ.get("FULLET_ALLOW_DB_WRITE") != "1":
        print("[SAFE] Set FULLET_ALLOW_DB_WRITE=1 to quarantine live data.")
        return 1

    url = _env("SUPABASE_URL")
    key = _env("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY", "SUPABASE_KEY")
    if not url or not key:
        print("[FAIL] Supabase env values are missing.")
        return 1

    supabase = create_client(url, key)
    rows = []
    start = 0
    while True:
        page = (
            supabase.table("istasyonlar")
            .select("id,marka,isim,il,ilce,enlem,boylam,aktif,veri_kaynagi")
            .range(start, start + 999)
            .execute()
            .data
            or []
        )
        rows.extend(page)
        if len(page) < 1000:
            break
        start += 1000

    to_deactivate = [row["id"] for row in rows if not _is_verified_station(row)]
    to_activate = [row["id"] for row in rows if _is_verified_station(row)]

    for batch in _chunks(to_deactivate):
        supabase.table("istasyonlar").update({"aktif": False}).in_("id", batch).execute()
    for batch in _chunks(to_activate):
        supabase.table("istasyonlar").update({"aktif": True}).in_("id", batch).execute()

    print(f"[OK] scanned={len(rows)} verified_active={len(to_activate)} quarantined={len(to_deactivate)}")
    if not to_activate:
        print("[OK] No official source is configured yet; app will not show questionable prices.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
