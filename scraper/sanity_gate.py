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

Kapı yakıt bazında çalışır: LPG reddedilse bile aynı koşudaki Motorin ve
Kurşunsuz 95 yazılmaya devam eder. Kısmi veri, sahte veriden iyidir.

İkinci kural KAYNAK BÜTÜNLÜĞÜdür (4 Ağustos 2026, Aytemiz vakası):

    Bir yakıt reddedildiyse, aynı koşudaki KARDEŞ yakıtlar da şüphe
    eşiğini (SIBLING_SUSPICION_DEVIATION) aşıyorsa onlar da yazılmaz.

Çünkü hepsi aynı HTML tablosundan, aynı ayrıştırıcıyla gelir. Aytemiz'de
Motorin %18,9 sapıp reddedilirken Benzin %5,6 ile eşiği geçti — ve geçen o
fiyat 81 ilin 79'unda "en ucuz" çıkarak kullanıcıyı yanlış istasyona
yönlendirdi.

Kural kasten dar tutuldu: Shell LPG hatasında Motorin %0,3 ile tertemizdi ve
yazılmaya devam etmeliydi. Sorun tek kolondaysa kardeşine dokunulmaz; kardeşi
de sapıyorsa tablonun bütünü şüphelidir.
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

# Kardeş yakıt şüphe eşiği (bkz. KAYNAK BÜTÜNLÜĞÜ kuralı).
#
# Yalnızca aynı koşuda BAŞKA bir yakıt reddedilmişse uygulanır; tek başına
# bu kadar sapan bir yakıt normal yolla yazılır. Değer canlı veriyle
# kalibre edildi:
#
#     Shell  Motorin (sağlam, LPG bozukken)  -> %0,3   yazılmalı
#     Aytemiz Benzin (bozuk, Motorin bozuk)  -> %4,9   yazılmamalı
#
# Markalar arası gerçek fark kuruş mertebesinde (canlı ölçüm: iller arası
# medyan fark %0,1), dolayısıyla %3 zaten anormaldir. Eşik bu iki gözlemin
# ortasında değil, sağlam tarafa yakın seçildi: amaç sağlam veriyi korumak.
SIBLING_SUSPICION_DEVIATION = 0.03


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
                .order("id")
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

    sapmalar: dict[str, float] = {}
    for fuel, values in incoming.items():
        if len(values) < MIN_SAMPLES_FOR_GATE:
            continue
        reference_median = reference.get(fuel)
        if not reference_median:
            continue
        incoming_median = statistics.median(values)
        deviation = abs(incoming_median - reference_median) / reference_median
        sapmalar[fuel] = deviation
        if deviation > MAX_MEDIAN_DEVIATION:
            rejected.add(fuel)
            reasons[fuel] = (
                f"{brand} {fuel} medyanı {incoming_median:.2f} TL; diğer markaların "
                f"medyanı {reference_median:.2f} TL (sapma %{deviation * 100:.1f} > "
                f"%{MAX_MEDIAN_DEVIATION * 100:.0f}). Kolon/birim hatası şüphesi — "
                f"bu yakıt YAZILMADI."
            )

    # KAYNAK BÜTÜNLÜĞÜ (4 Ağustos 2026, Aytemiz vakası).
    #
    # Ana kural yakıt bazındadır ve bu bilinçliydi: Shell LPG hatasında LPG
    # %20 sapmıştı ama Motorin %0,3 ile tertemizdi — onu da atmak, sağlam
    # veriyi çöpe atmak olurdu.
    #
    # Aytemiz o ilkenin sınırını gösterdi. Aynı HTML tablosundan gelen iki
    # fiyatın İKİSİ de sapıyordu, ama yalnızca biri eşiği aşabildi:
    #
    #     Motorin  67,17 TL  (piyasa 82,14)  -> sapma %18,9  REDDEDİLDİ
    #     Benzin   64,86 TL  (piyasa 68,20)  -> sapma  %5,6  GEÇTİ
    #
    # Geçen benzin fiyatı 81 ilin 79'unda "en ucuz" çıkıp kullanıcıyı yanlış
    # istasyona yönlendirdi.
    #
    # Ayrım şudur: kardeş yakıt TEMİZSE (Shell Motorin %0,3) kaynak sağlamdır,
    # sorun tek kolondadır. Kardeş yakıt da ANLAMLI ölçüde sapıyorsa
    # (Aytemiz Benzin %5,6) tablonun bütünü şüphelidir. Eşik için bkz.
    # SIBLING_SUSPICION_DEVIATION: tek başına kabul edilebilir bir sapma, ama
    # kardeşi bozukken güvenilmez.
    supheli_esik = SIBLING_SUSPICION_DEVIATION
    if rejected:
        for fuel, sapma in sapmalar.items():
            if fuel in rejected or sapma <= supheli_esik:
                continue
            reasons[fuel] = (
                f"{brand} {fuel} tek başına eşiği geçiyordu (sapma "
                f"%{sapma * 100:.1f} < %{MAX_MEDIAN_DEVIATION * 100:.0f}) ama aynı "
                f"koşuda {', '.join(sorted(rejected))} reddedildi ve bu yakıt da "
                f"şüphe eşiğinin (%{supheli_esik * 100:.0f}) üstünde sapıyor. Hepsi "
                f"aynı kaynak tablosundan geliyor — kaynağın bütünlüğü şüpheli "
                f"olduğu için bu yakıt da YAZILMADI."
            )
            rejected.add(fuel)

    return rejected, reasons


def apply_sanity_gate(
    items: list[dict[str, Any]],
    brand: str,
) -> tuple[list[dict[str, Any]], set[str]]:
    """Şüpheli yakıtları öğelerden çıkarır, alarm açar/kapatır.

    Döner: (filtrelenmiş öğeler, reddedilen yakıtlar). Yakıtı kalmayan öğeler
    tamamen elenir.

    Reddedilen yakıt kümesini ÇAĞIRANA döndürmek şart: `save_to_supabase`
    sonrasında "bu koşuda raporlanmayan yakıtları unknown yap" süpürgesi
    çalışıyor. Kapı bir yakıtı reddettiğinde o yakıt öğelerden düştüğü için
    süpürge onu "raporlanmadı" sayıp mevcut SAĞLAM fiyatları unknown'a
    çeviriyordu — yani kapı, koruması gereken veriyi siliyordu. Çağıran bu
    kümeyi süpürgeden muaf tutar (bkz. db_utils).
    """
    rejected, reasons = check_fuel_sanity(items, brand)
    source = f"sanity_gate:{brand}"

    if not rejected:
        resolve_system_alerts(source=source)
        return items, rejected

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
    return filtered, rejected
