"""Fiyat tazeliği için TEK tanım kaynağı.

Denetim öncesi dört bileşen dört farklı eşik kullanıyordu (yol haritası S0-4):

    pg_cron fresh->stale      12 saat
    pg_cron stale->unknown    48 saat
    quarantine_old_prices     72 saat
    ops_report                48 saat
    admin panel               72 saat

Sonuç: admin panel "Temiz" derken uygulama aynı fiyata "⚠️ Bayat" diyordu.
Artık tüm Python bileşenleri buradaki değerleri kullanır; SQL tarafındaki
karşılıkları database/add_price_verification.sql içinde aynı sayılarla
tanımlıdır (ikisi birlikte değiştirilmeli).

--- Neden `son_dogrulama` ayrı bir kolon? -------------------------------------

`son_guncelleme` iki farklı anlamda kullanılıyordu:

  * trigger `log_fiyat_degisimi`  -> "fiyatın son DEĞİŞTİĞİ an"
  * pg_cron tazelik işleri        -> "fiyatı son DOĞRULADIĞIMIZ an"

Türkiye'de fiyatlar ayda birkaç kez değiştiği için bu ikisi haftalarca
ayrışıyor. Üstüne bot diff'i "fiyat aynı + status fresh + yaş < 24s" ise
satırı tamamen atlıyordu; yani doğrulama izi hiç yazılmıyordu. 12 saatlik
cron eşiğiyle birleşince fiyat DOĞRUYKEN bayat işaretleniyordu:

    T+0h   bot yazar   -> fresh
    T+6h   bot koşar   -> fiyat aynı, yaş 6h < 24h  -> ATLA (iz yok)
    T+12h  cron        -> stale                      <- yanlış
    T+18h  bot koşar   -> status != fresh            -> yazar -> fresh

1 Ağustos canlı verisi bu döngüyü doğruladı: Opet/PO/Aytemiz/TP son yazımlarını
22:13'te yapmış, ertesi sabahki koşuda atlanmış ve 10:14'te bayada düşmüştü.

Ayrım: `son_guncelleme` artık yalnızca fiyat değiştiğinde ilerler,
`son_dogrulama` her başarılı kazımada ilerler. Tazelik `son_dogrulama`'ya bakar.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

# Kaynak siteler günde birkaç kez güncelleniyor, botlar 6 saatte bir koşuyor.
# 12 saat = iki koşu kaçırılmış demektir; bu noktada fiyat "doğrulanmış"
# sayılmaz.
FRESH_MAX_HOURS = 12

# 48 saat sonrasında fiyat gösterilmeye değmez; "bilinmiyor"a düşer.
STALE_MAX_HOURS = 48

# Aynı koşunun (veya art arda tetiklenen manuel koşuların) aynı satırı
# defalarca yazmasını engelleyen idempotenslik payı. Bot cadence'inden (6s)
# küçük olmalı, yoksa doğrulama izi yine atlanır.
VERIFY_DEBOUNCE_HOURS = 1


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(value) -> datetime | None:
    """ISO 8601 metnini tz-aware UTC datetime'a çevirir."""
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def age_hours(value, *, reference: datetime | None = None) -> float | None:
    parsed = parse_timestamp(value)
    if parsed is None:
        return None
    return ((reference or now_utc()) - parsed).total_seconds() / 3600


def status_for_age(hours: float | None) -> str:
    """Doğrulama yaşına karşılık gelen price_status."""
    if hours is None:
        return "unknown"
    if hours <= FRESH_MAX_HOURS:
        return "fresh"
    if hours <= STALE_MAX_HOURS:
        return "stale"
    return "unknown"


def needs_verification_write(
    last_verified,
    current_status: str | None,
    *,
    reference: datetime | None = None,
) -> bool:
    """Fiyat değişmediğinde doğrulama izinin yazılması gerekip gerekmediği.

    Status zaten 'fresh' DEĞİLSE her zaman yazılır (bayat -> taze geçişi).
    'fresh' ise yalnızca debounce penceresi dolduysa yazılır.
    """
    if current_status != "fresh":
        return True
    hours = age_hours(last_verified, reference=reference)
    if hours is None:
        return True
    return hours >= VERIFY_DEBOUNCE_HOURS


def stale_cutoff(*, reference: datetime | None = None) -> datetime:
    return (reference or now_utc()) - timedelta(hours=FRESH_MAX_HOURS)


def unknown_cutoff(*, reference: datetime | None = None) -> datetime:
    return (reference or now_utc()) - timedelta(hours=STALE_MAX_HOURS)
