from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

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
    
    # Mark prices older than 72 hours as 'stale' instead of deleting them
    cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
    
    print(f"Marking prices older than {cutoff_time} as stale...")
    try:
        # Fixed column name from guncellenme_tarihi to son_guncelleme
        result = (
            supabase.table("fiyatlar")
            .update({"price_status": "stale"})
            .lt("son_guncelleme", cutoff_time)
            .neq("price_status", "stale")
            .execute()
        )
        stale_count = len(result.data) if result.data else 0
        print(f"[OK] Marked {stale_count} price records as stale.")
    except Exception as e:
        print(f"[FAIL] Error updating old prices: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
