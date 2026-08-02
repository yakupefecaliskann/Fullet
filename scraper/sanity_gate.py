"""Yazma öncesi çapraz doğrulama kapısı.

Shell LPG hatası (yol haritası S1-1) aylarca fark edilmedi çünkü hiçbir katman
"bu sayı diğer markalara göre makul mü?" diye sormuyordu. `parse_price` yalnızca
0 < fiyat < 300 kontrolü yapıyor; kilogram başına fuel oil fiyatı (38,51) bu
aralığa rahatça giriyor ve litre başına LPG diye yazılıyordu.

Bu modül tek bir kural uygular:

    Bir markanın bir yakıttaki MEDYANI, aynı yakıtta diğer markaların
    medyanından %10'dan fazla sapıyorsa -> o yakıt YAZILMAZ, critical alarm.

Kural neden medyan? Tek tek istasyon fiyatları meşru biçimde dalgalanır
(bölgesel farklar), ama bir markanın ülke geneli medyanı diğerlerinden %10
sapıyorsa bu coğrafya değil **birim/kolon hatasıdır**. Shell LPG'de sapma
%20 idi — bu kural onu ilk gün yakalardı.

Kapı, yakıt bazında çalışır: LPG reddedilse bile aynı koşudaki Motorin ve
Kurşunsuz 95 yazılmaya devam eder. Kısmi veri, sahte veriden iyidir.
"""

from __future__ import annotations

import statistics
from typing import Any, Iterable

from config import supabase
from telemetry import create_system_alert, resolve_system_alerts

# Medyan sapma toleransı. %10, bölgesel fiyat farklarının çok üstünde
# (canlı ölçüm: iller arası medyan fark %0,1) ama birim hatalarının
# (kg<->lt, ~%20) çok altında.
MAX_MEDIAN_DEVIATION = 0.10

# Bu sayının altında örnek varsa medyan anlamlı değil; kapı uygulanmaz.
MIN_SAMPLES_FOR_GATE = 5


_PAGE_SIZE = 1000


def _reference_medians(exclude_brand: str) -> dict[str, float]:
    """Diğer markaların yakıt bazlı medyan fiyatları (yalnızca taze/bayat).

    PostgREST varsayılan olarak 1000 satır döndürür; sayfalama olmadan
    tablonun büyük kısmı görülmez ve az sayıda kayda sahip yakıtlar
    (ör. LPG) referanstan tamamen düşer — kapı da sessizce devre dışı kalır.
    """
    if supabase is None:
        return {}

    rows: list[dict[str, Any]] = []
    start = 0
    try:
        while True:
            page = (
                supabase.table("fiyatlar")
                .select("yakit_tipi, fiyat, price_status, istasyonlar!inner(marka)")
                .neq("price_status", "unknown")
                .range(start, start + _PAGE_SIZE - 1)
                .execute()
                .data
                or []
            )
            rows.extend(page)
            if len(page) < _PAGE_SIZE:
                break
            start += _PAGE_SIZE
    except Exception as exc:
        print(f"[WARN] Çapraz doğrulama referansı okunamadı: {exc}")
        return {}

    by_fuel: dict[str, list[float]] = {}
    for row in rows:
        station = row.get("istasyonlar") or {}
        brand = station.get("marka") if isinstance(station, dict) else None
        if not brand or brand == exclude_brand:
            continue
        price = row.get("fiyat")
        fuel = row.get("yakit_tipi")
        if fuel is None or price is None:
            continue
        try:
            by_fuel.setdefault(fuel, []).append(float(price))
        except (TypeError, ValueError):
            continue

    return {
        fuel: statistics.median(values)
        for fuel, values in by_fuel.items()
        if len(values) >= MIN_SAMPLES_FOR_GATE
    }


def _incoming_medians(items: Iterable[dict[str, Any]]) -> dict[str, list[float]]:
    by_fuel: dict[str, list[float]] = {}
    for item in items:
        for fuel, price in (item.get("fiyatlar") or {}).items():
            try:
                by_fuel.setdefault(fuel, []).append(float(price))
            except (TypeError, ValueError):
                continue
    return by_fuel


def check_fuel_sanity(
    items: list[dict[str, Any]],
    brand: str,
) -> tuple[set[str], dict[str, str]]:
    """Yazılmaması gereken yakıtları belirler.

    Döner: (reddedilen yakıtlar, yakıt -> gerekçe metni)
    """
    rejected: set[str] = set()
    reasons: dict[str, str] = {}

    incoming = _incoming_medians(items)
    if not incoming:
        return rejected, reasons

    reference = _reference_medians(brand)
    if not reference:
        # Karşılaştırılacak marka yok (ilk kurulum / tek marka) — kapı sessizce
        # devre dışı. Veri yokluğunda yazmayı engellemek daha zararlı olurdu.
        return rejected, reasons

    for fuel, values in incoming.items():
        if len(values) < MIN_SAMPLES_FOR_GATE:
            continue
        reference_median = reference.get(fuel)
        if not reference_median:
            continue
        incoming_median = statistics.median(values)
        deviation = abs(incoming_median - reference_median) / reference_median
        if deviation > MAX_MEDIAN_DEVIATION:
            rejected.add(fuel)
            reasons[fuel] = (
                f"{brand} {fuel} medyanı {incoming_median:.2f} TL; diğer markaların "
                f"medyanı {reference_median:.2f} TL (sapma %{deviation * 100:.1f} > "
                f"%{MAX_MEDIAN_DEVIATION * 100:.0f}). Kolon/birim hatası şüphesi — "
                f"bu yakıt YAZILMADI."
            )
    return rejected, reasons


def apply_sanity_gate(items: list[dict[str, Any]], brand: str) -> list[dict[str, Any]]:
    """Şüpheli yakıtları öğelerden çıkarır, alarm açar/kapatır.

    Yakıtı kalmayan öğeler tamamen elenir.
    """
    rejected, reasons = check_fuel_sanity(items, brand)
    source = f"sanity_gate:{brand}"

    if not rejected:
        resolve_system_alerts(source=source)
        return items

    for fuel in sorted(rejected):
        print(f"[CRITICAL] {reasons[fuel]}")
        create_system_alert(
            severity="critical",
            source=source,
            title=f"{brand} {fuel} çapraz doğrulamayı geçemedi",
            message=reasons[fuel],
            metadata={"brand": brand, "fuel": fuel},
        )

    filtered: list[dict[str, Any]] = []
    for item in items:
        prices = {
            fuel: price
            for fuel, price in (item.get("fiyatlar") or {}).items()
            if fuel not in rejected
        }
        if not prices:
            continue
        filtered.append({**item, "fiyatlar": prices})
    return filtered
