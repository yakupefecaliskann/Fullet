from __future__ import annotations

import os
import sys
from collections import defaultdict
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
        print("[SAFE] Set FULLET_ALLOW_DB_WRITE=1 to delete duplicate stations.")
        return 1

    url = _env("SUPABASE_URL")
    key = _env("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY", "SUPABASE_KEY")
    if not url or not key:
        print("[FAIL] Supabase env values are missing.")
        return 1

    supabase = create_client(url, key)
    
    print("Fetching all stations...")
    rows = []
    start = 0
    while True:
        page = (
            supabase.table("istasyonlar")
            .select("id, marka, isim, il, ilce, enlem, boylam, aktif")
            .range(start, start + 999)
            .execute()
            .data
            or []
        )
        rows.extend(page)
        if len(page) < 1000:
            break
        start += 1000

    print(f"Found {len(rows)} stations in total.")
    
    # Group by (marka, il, ilce, round(enlem, 4), round(boylam, 4))
    groups = defaultdict(list)
    for row in rows:
        lat = row.get("enlem")
        lng = row.get("boylam")
        if lat is None or lng is None:
            continue
            
        key = (
            row["marka"],
            row["il"],
            row["ilce"],
            round(lat, 4),
            round(lng, 4)
        )
        groups[key].append(row)

    to_delete = []
    
    for key, group in groups.items():
        if len(group) > 1:
            # Sort by "aktif" (True first) so we keep the active one
            group.sort(key=lambda x: (x.get("aktif", False)), reverse=True)
            
            kept = group[0]
            duplicates = group[1:]
            
            for d in duplicates:
                to_delete.append(d["id"])
                print(f"Duplicate found: {d['isim']} (ID: {d['id']}) -> keeping {kept['isim']} (ID: {kept['id']})")

    if not to_delete:
        print("[OK] No duplicate stations found.")
        return 0
        
    print(f"Deleting {len(to_delete)} duplicate stations...")
    
    # Supabase in_ clause has limits, process in chunks of 100
    for i in range(0, len(to_delete), 100):
        batch = to_delete[i:i+100]
        try:
            supabase.table("istasyonlar").delete().in_("id", batch).execute()
        except Exception as e:
            print(f"[FAIL] Error deleting batch: {e}")
            
    print(f"[OK] Cleaned up {len(to_delete)} duplicates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
