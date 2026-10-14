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
from freshness import STALE_MAX_HOURS
from known_outages import active_outage_for_brand

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

# Tek tanım kaynağı: scraper/freshness.py (yol haritası S0-4).
MAX_PRICE_AGE_HOURS = STALE_MAX_HOURS
VERIFIED_SOURCES = OFFICIAL_REGIONAL_SOURCES | OFFICIAL_STATION_SOURCES

# RLS'in anon rolüne açtığı görünürlük durumları — `rls_policies.sql`,
# "public read istasyonlar" politikasının allowlist'iyle BİREBİR aynı olmalı.
#
# 14 Ekim 2026 denetimi, §D-7: bu rapor yalnızca `aktif=true` sayıyordu ve
# `visibility_status`'a hiç bakmıyordu. Shell kaynağı 9 Eylül'de ölünce
# `fullet-resolve-station-visibility` cron'u 1309 istasyonu `hidden` yaptı —
# ama rapor 33 gün boyunca "Total active stations: 6992" yazmaya devam etti.
# Sahibin baktığı tek özet sayı, kullanıcı gerçeğini 1309 istasyon FAZLA
# gösteriyordu; yani ürünün beşte biri karanlıktayken rapor sakin görünüyordu.
#
# Allowlist (RLS'i aynen yansıtmak) bilinçli olarak `!= 'hidden'` yerine
# seçildi: yeni bir durum değeri eklenirse RLS onu anon'dan saklar, ve bu
# listeyi güncellemeyi unutmak raporu yine yalancı yapardı. Aynı listeyi
# kullanmak, sapmayı ilk koşuda görünür kılar.
USER_VISIBLE_STATUSES = frozenset({"visible", "low_priority"})


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
            .select(
                "id,marka,il,aktif,veri_kaynagi,guncellenme_tarihi,"
                "visibility_status"
            )
            .eq("marka", brand)
            .order("id")
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
            .select("istasyon_id,yakit_tipi,fiyat,son_guncelleme,son_dogrulama")
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
    print("=" * 85)
    # "Shown" ilk sütun ve kasıtlı: raporu okuyan kişinin güvenmesi gereken
    # sayı budur. "Active" veritabanı gerçeğini, "Shown" KULLANICI gerçeğini
    # söyler ve ikisi ayrışabilir (bkz. USER_VISIBLE_STATUSES).
    print(
        f"{'Brand':<20} {'Shown':>6} {'Active':>6} {'Total':>6} {'Prices':>7} "
        f"{'City':>4} {'Fuels':<22} {'Latest':>7}"
    )
    print("-" * 85)

    total_active = 0
    total_visible = 0
    total_prices = 0
    warnings = []

    for brand in BRANDS:
        stations = _select_brand_stations(brand)
        active = [row for row in stations if row.get("aktif") is True]
        visible = [
            row for row in active
            if (row.get("visibility_status") or "") in USER_VISIBLE_STATUSES
        ]
        prices = _select_prices([row["id"] for row in active])
        fuels = Counter(row.get("yakit_tipi") for row in prices)
        # Tazelik `son_dogrulama`'ya bakar, `son_guncelleme`'ye DEĞİL:
        # birincisi her başarılı kazımada, ikincisi yalnızca fiyat
        # değiştiğinde ilerler (bkz. freshness.py). Bu ayrım S0-4'te
        # getirildi ama burası atlanmıştı; zam gelmeyen her 48 saatte
        # rapor sahte "stale price data" alarmı üretiyordu.
        # `or` geri düşüşü: doğrulama izi olmayan eski satırlar için.
        latest = max(
            [
                row.get("son_dogrulama") or row.get("son_guncelleme")
                for row in prices
                if row.get("son_dogrulama") or row.get("son_guncelleme")
            ],
            default=None,
        )
        active_cities = len({row.get("il") for row in active if row.get("il")})
        total_active += len(active)
        total_visible += len(visible)
        total_prices += len(prices)

        if not active:
            warnings.append(f"{brand}: no active stations")
        # Tam karartma: marka veritabanında duruyor ama kullanıcı TEK BİR
        # istasyonunu bile göremiyor. Shell'in 9 Eylül'den beri içinde olduğu
        # durum tam olarak bu ve hiçbir sinyal bunu söylemiyordu.
        #
        # KISMİ karartma kasıtlı olarak uyarı ÜRETMİYOR: tek tek istasyonların
        # fiyatını kaybedip gizlenmesi olağan dalgalanma: her koşuda uyarı
        # basmak S0-4'teki sahte "stale" gürültüsünü yeniden kurardı. Kısmi
        # fark "Shown" sütununda ve alttaki toplamda zaten görünüyor.
        elif not visible:
            warnings.append(
                f"{brand}: no user-visible stations "
                f"({len(active)} active, all hidden by visibility_status)"
            )
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
            f"{brand:<20} {len(visible):>6} {len(active):>6} {len(stations):>6} "
            f"{len(prices):>7} {active_cities:>4} {fuel_text[:22]:<22} "
            f"{_age_text(latest):>7}"
        )

    print("-" * 85)
    print(f"User-visible stations: {total_visible}")
    print(f"Total active stations: {total_active}")
    print(f"Total active prices: {total_prices}")
    if total_active != total_visible:
        hidden_total = total_active - total_visible
        share = (hidden_total / total_active * 100) if total_active else 0.0
        share_text = f"{share:.1f}".replace(".", ",")  # TR ondalık ayracı
        print(
            f"  -> {hidden_total} aktif istasyon KULLANICIYA GÖRÜNMÜYOR "
            f"(envanterin %{share_text}'si; visibility_status != visible)"
        )

    # --- Kabul edilmiş kaynak arızaları --------------------------------------
    # Kaynağı ölmüş bir markanın verisi elbette bayatlar; bunu her 6 saatte bir
    # kırmızıya çevirmek yeni bir bilgi taşımaz, sadece raporun kırmızısını
    # anlamsızlaştırır. Uyarı BASILIR ve alarmı AÇIK KALIR — yalnızca çıkış
    # kodunu tek başına belirlemez. Kaydın süresi dolduğunda (known_outages.py)
    # bu ayrıcalık kendiliğinden biter ve marka yeniden bloklayıcı olur.
    acknowledged = []
    blocking = []
    for warning in warnings:
        brand = warning.split(":", 1)[0]
        outage = active_outage_for_brand(brand)
        (acknowledged if outage else blocking).append((warning, outage))

    # Uyarısı OLMAYAN markaların eski alarmlarını kapat. Eskiden burada
    # koşulsuz `resolve_system_alerts(source="ops_report")` vardı ve yalnızca
    # HİÇ uyarı yokken çalışıyordu; tek bir kalıcı uyarı, düzelmiş bütün
    # markaların alarmlarını sonsuza dek açık bırakıyordu.
    warned_titles = {warning.split(":", 1)[0] for warning in warnings}
    for brand in BRANDS:
        if brand not in warned_titles:
            resolve_system_alerts(source="ops_report", title=brand)

    if warnings:
        print("\nWarnings")
        for warning, _ in blocking:
            print(f"[WARN] {warning}")
            create_system_alert(
                severity="warning",
                source="ops_report",
                title=warning.split(":", 1)[0],
                message=warning,
                metadata={"report": "live_data"},
            )
        for warning, outage in acknowledged:
            print(f"[BILINEN-ARIZA] {warning} — {outage.describe()}")
            create_system_alert(
                severity="warning",
                source="ops_report",
                title=warning.split(":", 1)[0],
                message=f"{warning} ({outage.describe()}; {outage.url})",
                metadata={
                    "report": "live_data",
                    "known_outage": True,
                    "review_by": outage.review_by.isoformat(),
                },
            )
        if blocking:
            return 1
        print(
            "\n[OK] Bloklayıcı uyarı yok; kalanların tamamı known_outages.py'de "
            "kayıtlı ve gözden geçirme tarihi henüz gelmedi."
        )
        return 0

    resolve_system_alerts(source="ops_report")
    # NOT: bot:* kaynaklı alarmlar burada KAPATILMAZ. Rapor istasyon/fiyat
    # SAYILARINA bakar, botun son koşusunun gerçekten başarılı olup olmadığına
    # değil — o alarmları yalnızca botun kendi başarılı koşusu kapatır
    # (run_all_bots.run_bot_with_retries). Eski "tolere edilen Shell" döneminden
    # kalan kör resolve satırları kalıcı Shell arızasını görünmez kılıyordu
    # (yol haritası S3-1).
    print("\n[OK] Live data operations report is clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
