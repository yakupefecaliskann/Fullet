from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

from freshness import (
    FRESH_MAX_HOURS,
    STALE_MAX_HOURS,
    stale_cutoff,
    unknown_cutoff,
)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "scraper" / ".env")


def _env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def main() -> int:
    if os.environ.get("FULLET_ALLOW_DB_WRITE") != "1":
        print("[SAFE] Set FULLET_ALLOW_DB_WRITE=1 to update old prices.")
        return 1

    url = _env("SUPABASE_URL")
    key = _env("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY", "SUPABASE_KEY")
    if not url or not key:
        print("[FAIL] Supabase env values are missing.")
        return 1

    supabase = create_client(url, key)

    # Eşikler tek kaynaktan (freshness.py) gelir; eskiden buradaki 72 saat
    # pg_cron'un 12/48 saatiyle ve admin panelin 72 saatiyle çelişiyordu
    # (yol haritası S0-4). Tazelik artık son_dogrulama'ya bakar: fiyatın son
    # DEĞİŞTİĞİ an değil, son DOĞRULANDIĞI an (bkz. freshness.py).
    stale_cut = stale_cutoff().isoformat()
    unknown_cut = unknown_cutoff().isoformat()

    print(
        f"Tazelik bakımı — fresh>stale: {FRESH_MAX_HOURS}s, "
        f"stale>unknown: {STALE_MAX_HOURS}s"
    )
    try:
        stale_result = (
            supabase.table("fiyatlar")
            .update({"price_status": "stale"})
            .lt("son_dogrulama", stale_cut)
            .eq("price_status", "fresh")
            .execute()
        )
        stale_count = len(stale_result.data) if stale_result.data else 0

        unknown_result = (
            supabase.table("fiyatlar")
            .update({"price_status": "unknown"})
            .lt("son_dogrulama", unknown_cut)
            .eq("price_status", "stale")
            .execute()
        )
        unknown_count = len(unknown_result.data) if unknown_result.data else 0

        print(f"[OK] {stale_count} fiyat bayat, {unknown_count} fiyat bilinmiyor olarak işaretlendi.")
    except Exception as e:
        print(f"[FAIL] Error updating old prices: {e}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
