"""Bilinen ve KABUL EDİLMİŞ kaynak arızalarının tek kaydı.

Neden bu dosya var
------------------
9 Eylül 2026'da Shell `/pompatest/` uygulamasını emekliye ayırdı. Bu bir bot
hatası değil, kaynağın ölümü — düzeltilecek kod yok. Ama sonucu şuydu: her
`prices` koşusu (günde 4) `run_all_bots`, `backend_health_check` ve
`ops_report` üçlüsünden kırmızı dönmeye başladı. Dokuz gün sonra pipeline'ın
kırmızı olması hiçbir şey ifade etmiyordu: **tp_bot yarın kırılsa kimse fark
etmezdi**, çünkü bakılacak sinyal zaten kırmızıydı.

Bu, projenin daha önce iki kez savaştığı hatanın aynısı, sadece ters yönü:
- S0-2'de `FULLET_FAIL_ON_BOT_ERROR=0` tüm alarmları SESSİZE almıştı.
- S0-4'te `ops_report` sahte "stale" alarmıyla 13 gün boyunca GÜRÜLTÜ yaptı.
Her iki durumda da kaybedilen şey aynı: sinyalin anlamı.

Neden `TOLERATED_FAILURE_BOTS` değil
------------------------------------
`run_all_bots.TOLERATED_FAILURE_BOTS` bir zamanlar tam da bunun için vardı ve
KASITLI olarak boşaltıldı (bkz. oradaki yorum, denetim Y1): bir botu topluca
"tolere edilen" ilan etmek, kaynağın ölümünü de PARSER KIRIKLIĞINI da aynı
anda gizler ve hiçbir zaman sona ermez. Buradaki kayıt üç noktada ondan ayrılır:

1. **Sadece çalışma anında DOĞRULANMIŞ tek bir imzayı** susturur: bot
   `EXIT_SOURCE_GONE` ile çıkmalı, ki bunu yalnızca kaynağın gerçekten
   erişilemez/tanınmaz olduğunu kanıtladığında yapar (`shell_bot._verify_source`).
   Parser kırılıp 0 kayıt dönerse çıkış kodu yine 1'dir ve pipeline yine kırmızı.
2. **Süresi dolar.** `review_by` geçtiğinde kayıt susturmayı BIRAKIR ve sağlık
   kontrolü "bu arıza gözden geçirilmedi" diye kırmızıya döner. Kalıcı bir göz
   bağı hâline gelemez.
3. **Kendini temizletir.** Kaydı olan bot yeniden başarılı olursa sağlık
   kontrolü kırmızıya döner ve kaydın SİLİNMESİNİ ister — yoksa geri dönmüş bir
   kaynağın gelecekteki gerçek arızası sessizce yutulurdu.

Kayıt eklerken `reason` alanına kaynağın NEDEN öldüğünü ve hangi alternatiflerin
elendiğini yaz; altı hafta sonra o satırı okuyan kişi (muhtemelen sensin) aynı
araştırmayı baştan yapmasın.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

# Bot'un "kaynağı doğruladım, ayakta değil" demek için kullandığı çıkış kodu.
# 1'den ayrı olması şart: 1 "bir şeyler ters gitti" demektir ve bir parser
# kırıklığını da kapsar. 3 yalnızca "gidilecek yer yok" anlamına gelir ve
# ancak burada kaydı olan bir bot için hoş görülür.
EXIT_SOURCE_GONE = 3


@dataclass(frozen=True)
class KnownOutage:
    """Kabul edilmiş tek bir kaynak arızası."""

    bot: str
    brand: str | None
    url: str
    reason: str
    since: date
    review_by: date

    def is_expired(self, today: date | None = None) -> bool:
        return (today or _today()) > self.review_by

    def days_left(self, today: date | None = None) -> int:
        return (self.review_by - (today or _today())).days

    def describe(self, today: date | None = None) -> str:
        today = today or _today()
        if self.is_expired(today):
            return (
                f"bilinen arıza kaydının gözden geçirme tarihi "
                f"({self.review_by}) GEÇTİ ({-self.days_left(today)} gün önce)"
            )
        return (
            f"bilinen arıza ({self.since} tarihinden beri), "
            f"gözden geçirme {self.review_by} ({self.days_left(today)} gün kaldı)"
        )


def _today() -> date:
    return datetime.now(timezone.utc).date()


KNOWN_OUTAGES: tuple[KnownOutage, ...] = (
    KnownOutage(
        bot="shell_bot.py",
        brand="Shell",
        url="https://www.turkiyeshell.com/pompatest/History.aspx",
        reason=(
            "Shell /pompatest/ uygulamasını emekliye ayırdı: adres HTTP 404 "
            "döndürüyor ve turkiyeshell.com artık yalnızca Taşıt Tanıma "
            "portalı (18 Eyl 2026'da yeniden doğrulandı; sitemap/robots yok, "
            "fiyat sayfasına bağlantı yok). Yedek kanal da elendi: "
            "find.shell.com fiyat şemasını taşıyor ama TR için "
            "fuel_pricing.status='unavailable'. Geriye yalnızca üçüncü taraf "
            "toplayıcılar kalıyor — bu provenance düşüşü ve ToS riski demek, "
            "karar ürün sahibinin."
        ),
        since=date(2026, 9, 9),
        review_by=date(2026, 10, 31),
    ),
)


def outage_for_bot(bot: str, today: date | None = None) -> KnownOutage | None:
    """Süresi dolmuş olsa DA kaydı döner — çağıran `is_expired()` ile karar verir."""
    for outage in KNOWN_OUTAGES:
        if outage.bot == bot:
            return outage
    return None


def active_outage_for_bot(bot: str, today: date | None = None) -> KnownOutage | None:
    """Yalnızca HÂLÂ GEÇERLİ kaydı döner. Susturma kararı bunu kullanmalı."""
    outage = outage_for_bot(bot)
    if outage is None or outage.is_expired(today):
        return None
    return outage


def outage_for_brand(brand: str, today: date | None = None) -> KnownOutage | None:
    for outage in KNOWN_OUTAGES:
        if outage.brand == brand:
            return outage
    return None


def active_outage_for_brand(brand: str, today: date | None = None) -> KnownOutage | None:
    outage = outage_for_brand(brand)
    if outage is None or outage.is_expired(today):
        return None
    return outage
