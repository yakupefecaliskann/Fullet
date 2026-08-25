"""Eski Shell LPG kolon hatasından kalan fosil satırları temizler.

ARKA PLAN
---------
S1-1 hatasında Shell ızgarasının 10. kolonu ("Yüksek Kükürtlü Fuel Oil,
TL/Kg") LPG (TL/Lt) diye yazılmıştı. Kazıyıcı düzeltildi (bkz.
column_mapping.py birim kapısı) ama YAZILMIŞ SATIRLAR TEMİZLENMEDİ.

25 Ağu 2026 canlı ölçüm: 466 Shell LPG satırı `unknown` durumunda,
son doğrulama Mayıs-Haziran 2026, değerler 38,51-44,81 TL — piyasa LPG
medyanı 34,04 TL. Bu satırlar tazelenmiyor çünkü kaynakta o ilçelerin
Otogaz kolonu "-" (istasyon LPG satmıyor).

`unknown` satırlar uygulamada gizlendiği için (`FuelPrice.isDisplayable`)
kullanıcıya görünmüyorlar; risk, ileride bir hatanın onları yeniden
görünür kılması ve admin panel/analitik sayılarını kirletmeleridir.

KULLANIM
--------
    python repair_shell_lpg_fossils.py            # kuru çalıştırma (varsayılan)
    FULLET_ALLOW_DB_WRITE=1 python repair_shell_lpg_fossils.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

from freshness import STALE_MAX_HOURS, unknown_cutoff

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

load_dotenv(Path(__file__).resolve().parent / ".env")

# Fuel oil TL/Kg değerleri LPG TL/Lt'den belirgin yüksekti. Piyasa LPG üst
# sınırının üstündeki her Shell LPG satırı şüphelidir; eşiği geniş tutuyoruz
# ki gerçek bir LPG fiyatı yanlışlıkla silinmesin.
SUSPICIOUS_LPG_MIN = 37.0


def _env(*names):
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _fetch_all(table, select, **filters):
    """Sayfalanmış tam okuma.

    `.order("id")` ŞART: ORDER BY'sız sayfalamada PostgREST satır sırasını
    garanti etmez, sayfalar arasında satır kaybı/tekrarı olur. Depodaki
    kural test_cleanup_regressions.PaginationOrderTest ile zorunlu tutuluyor.
    """
    rows, start = [], 0
    while True:
        query = table.select(select)
        for column, value in filters.items():
            query = query.eq(column, value)
        page = query.order("id").range(start, start + 999).execute().data or []
        rows.extend(page)
        if len(page) < 1000:
            return rows
        start += 1000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Satırları gerçekten sil (ayrıca FULLET_ALLOW_DB_WRITE=1 gerekir).",
    )
    args = parser.parse_args()

    url = _env("SUPABASE_URL")
    key = _env("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY", "SUPABASE_KEY")
    if not url or not key:
        print("[FAIL] Supabase env değerleri eksik.")
        return 1
    supabase = create_client(url, key)

    shell_ids = {
        row["id"]
        for row in _fetch_all(supabase.table("istasyonlar"), "id,marka", marka="Shell")
    }
    print(f"Shell istasyonu: {len(shell_ids)}")

    prices = _fetch_all(
        supabase.table("fiyatlar"),
        "id,istasyon_id,fiyat,price_status,son_dogrulama",
        yakit_tipi="LPG",
    )
    cutoff = unknown_cutoff().isoformat()
    fossils = [
        row
        for row in prices
        if row["istasyon_id"] in shell_ids
        and row.get("price_status") == "unknown"
        and (row.get("son_dogrulama") or "") < cutoff
        and (row.get("fiyat") or 0) >= SUSPICIOUS_LPG_MIN
    ]

    print(f"LPG satırı (tüm markalar) : {len(prices)}")
    print(f"Fosil aday (Shell/unknown/>{SUSPICIOUS_LPG_MIN} TL/>{STALE_MAX_HOURS}s): {len(fossils)}")
    if fossils:
        values = sorted(row["fiyat"] for row in fossils)
        print(f"  fiyat aralığı: {values[0]:.2f} - {values[-1]:.2f} TL")
        oldest = min(row["son_dogrulama"] for row in fossils)
        print(f"  en eski doğrulama: {oldest[:10]}")

    if not fossils:
        print("[OK] Temizlenecek fosil satır yok.")
        return 0

    if not args.apply:
        print("\n[KURU] --apply verilmedi, hiçbir şey silinmedi.")
        return 0
    if os.environ.get("FULLET_ALLOW_DB_WRITE") != "1":
        print("\n[SAFE] Silmek için FULLET_ALLOW_DB_WRITE=1 gerekir.")
        return 1

    ids = [row["id"] for row in fossils]
    for start in range(0, len(ids), 200):
        chunk = ids[start : start + 200]
        supabase.table("fiyatlar").delete().in_("id", chunk).execute()
        print(f"  silindi: {start + len(chunk)}/{len(ids)}")
    print(f"[OK] {len(ids)} fosil LPG satırı silindi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
