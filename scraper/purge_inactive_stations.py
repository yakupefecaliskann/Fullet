"""Uzun süredir pasif kalmış istasyon kayıtlarını siler (moloz temizliği).

Varsayılan DRY-RUN'dır. Yazmak için `FULLET_ALLOW_DB_WRITE=1`.

--- Neden gerekli? -----------------------------------------------------------

`matching._station_inventory_target` envanterde görüp doğrulayamadığı
istasyonu `aktif=False` ile yazar. Bu doğru davranıştır — ama kayıt bir daha
hiç doğrulanmazsa sonsuza kadar birikir. Canlı ölçüm (3 Ağustos 2026):
544 pasif istasyon, 729 fiyat satırı, 2.047 fiyat geçmişi satırı. Fiyat
satırlarının **tamamı** `unknown`'dı, yani tek bir gösterilebilir fiyat yoktu.

--- Neden 30 gün? ------------------------------------------------------------

Pasif olmak "silinmeli" demek DEĞİLDİR: envanter botu haftada bir koşar ve
bir istasyonu geçici olarak pasife düşürebilir. 30 gün, haftalık koşunun dört
turudur — bu kadar süre boyunca hiçbir botun dokunmadığı kayıt gerçekten ölüdür.
Ölçüm bunu destekliyor: 544 pasif kaydın 542'si 30+ gündür dokunulmamıştı,
kalan 2'si İstanbul'un split-region reset döngüsündeydi.

--- Ne SİLİNMEZ? -------------------------------------------------------------

* Aktif istasyonlar (görünür olsun olmasın).
* Favorisi veya fiyat alarmı olan kayıtlar — `ON DELETE CASCADE` yüzünden
  sessizce kaybolurlardı. Bunlar atlanır ve raporlanır.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from config import supabase

INACTIVE_GRACE_DAYS = 30


def _page_all(table: str, select: str) -> list[dict]:
    """bkz. merge_duplicate_stations._page_all — `.order("id")` şart."""
    assert supabase is not None
    rows: list[dict] = []
    start = 0
    while True:
        page = (
            supabase.table(table).select(select).order("id").range(start, start + 999)
            .execute().data or []
        )
        rows.extend(page)
        if len(page) < 1000:
            break
        start += 1000
    return rows


def main() -> int:
    if supabase is None:
        print("[FAIL] Supabase env değerleri eksik.")
        return 1

    write_enabled = os.environ.get("FULLET_ALLOW_DB_WRITE") == "1"
    print(f"=== Pasif istasyon temizliği — {'UYGULAMA' if write_enabled else 'DRY-RUN'} ===")
    print(f"Eşik: {INACTIVE_GRACE_DAYS} gündür dokunulmamış pasif kayıtlar\n")

    cutoff = datetime.now(timezone.utc) - timedelta(days=INACTIVE_GRACE_DAYS)
    stations = (
        supabase.table("istasyonlar")
        .select("id,marka,isim,il,ilce,guncellenme_tarihi")
        .eq("aktif", False)
        .lt("guncellenme_tarihi", cutoff.isoformat())
        .order("id")
        .execute()
        .data
        or []
    )
    if not stations:
        print("[OK] Silinecek pasif istasyon yok.")
        return 0

    doomed = {s["id"] for s in stations}
    protected: dict[str, str] = {}
    for favorite in _page_all("fullet_favorites", "station_id"):
        if favorite["station_id"] in doomed:
            protected[favorite["station_id"]] = "favori"
    for alert in _page_all("price_alerts", "istasyon_id"):
        if alert.get("istasyon_id") in doomed:
            protected[alert["istasyon_id"]] = "fiyat alarmı"

    deletable = [s for s in stations if s["id"] not in protected]
    by_brand: dict[str, int] = {}
    for station in deletable:
        by_brand[station.get("marka") or "?"] = by_brand.get(station.get("marka") or "?", 0) + 1

    print(f"Pasif ve {INACTIVE_GRACE_DAYS}+ gündür dokunulmamış: {len(stations)}")
    for brand, count in sorted(by_brand.items(), key=lambda kv: -kv[1]):
        print(f"    {brand:<22} {count}")
    if protected:
        print(f"\n[KORUNDU] {len(protected)} kayıt kullanıcı verisi taşıdığı için atlandı:")
        for station_id, reason in sorted(protected.items()):
            print(f"    {station_id} ({reason})")
    print(f"\nSilinecek: {len(deletable)} istasyon "
          f"(fiyat ve fiyat geçmişi satırları CASCADE ile gider)")

    if not write_enabled:
        print("\n[DRY-RUN] Hiçbir şey yazılmadı. Uygulamak için "
              "FULLET_ALLOW_DB_WRITE=1 ile tekrar çalıştırın.")
        return 0

    ids = [s["id"] for s in deletable]
    for batch_start in range(0, len(ids), 100):
        supabase.table("istasyonlar").delete().in_(
            "id", ids[batch_start:batch_start + 100]
        ).execute()
    print(f"[OK] {len(ids)} pasif istasyon silindi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
