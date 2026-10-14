"""ops_report tazelik muhasebesi testleri.

Bu dosyanın var oluş sebebi somut bir üretim arızası: S0-4 refaktörü
`son_guncelleme` ("fiyat en son NE ZAMAN DEĞİŞTİ") ile `son_dogrulama`
("fiyatı en son NE ZAMAN DOĞRULADIK") ayrımını getirdi ve tazeliğin
`son_dogrulama`'ya bakması gerektiğini freshness.py'de yazdı. Refaktör
admin paneline ve SQL'e uygulandı ama ops_report.py atlandı.

Sonuç: zam gelmeyen her 48 saatte ops_report "stale price data" deyip 1
döndürdü, otopilot workflow'u kırmızıya döndü ve 18-31 Ağustos 2026 arası
onlarca sahte alarm üretti — botlar kusursuz çalışırken.

Testler bu yüzden ÜÇ şeyi birden kilitler:
  1) doğrulama izi tazeyse alarm YOK           (yanlış pozitif dönmesin)
  2) doğrulama izi de bayatsa alarm VAR        (alarm sessizce kapanmasın)
  3) sorgu son_dogrulama kolonunu gerçekten İSTER
Üçü olmadan aynı hata tekrar sızabilir: (1) ve (2) olmadan mantık,
(3) olmadan da kolon sessizce None gelip (1)'i fallback'e düşürürdü.
"""

from __future__ import annotations

import unittest
import unittest.mock
from datetime import date, datetime, timedelta, timezone

import known_outages
import ops_report

VERIFIED_SOURCE = "api.opet.com.tr/api/fuelprices/allprices"
# MIN_ACTIVE_STATIONS / MIN_PRICE_ROWS bu markayı tanımıyor; .get(brand, 1)
# ile eşikler 1'e düşer, böylece testler sayı eşiklerine değil yalnızca
# tazeliğe bakar.
TEST_BRAND = "TestBrand"


def _iso(*, hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def _station(*, visibility: str = "visible", station_id: str = "st_1") -> dict:
    return {
        "id": station_id,
        "marka": TEST_BRAND,
        "il": "ISTANBUL",
        "aktif": True,
        "veri_kaynagi": VERIFIED_SOURCE,
        "guncellenme_tarihi": _iso(hours_ago=1),
        "visibility_status": visibility,
    }


def _price(*, changed_hours_ago: float, verified_hours_ago: float | None) -> dict:
    return {
        "istasyon_id": "st_1",
        "yakit_tipi": "Motorin",
        "fiyat": 52.5,
        "son_guncelleme": _iso(hours_ago=changed_hours_ago),
        "son_dogrulama": (
            None if verified_hours_ago is None else _iso(hours_ago=verified_hours_ago)
        ),
    }


class OpsReportFreshnessTest(unittest.TestCase):
    def _run_main(self, prices: list[dict], stations: list[dict] | None = None):
        """main()'i tek markalı sahte veriyle koşturur, (kod, alarmlar) döner."""
        alerts: list[dict] = []
        with unittest.mock.patch.object(ops_report, "supabase", unittest.mock.MagicMock()), \
             unittest.mock.patch.object(ops_report, "BRANDS", [TEST_BRAND]), \
             unittest.mock.patch.object(
                 ops_report, "_select_brand_stations",
                 return_value=stations if stations is not None else [_station()]), \
             unittest.mock.patch.object(
                 ops_report, "_select_prices", return_value=prices), \
             unittest.mock.patch.object(ops_report, "resolve_system_alerts"), \
             unittest.mock.patch.object(
                 ops_report, "create_system_alert",
                 side_effect=lambda **kw: alerts.append(kw)):
            code = ops_report.main()
        return code, alerts

    def test_recently_verified_price_is_not_stale(self):
        """Fiyat 5 gündür DEĞİŞMEDİ ama 1 saat önce DOĞRULANDI -> temiz.

        Üretimdeki asıl arıza buydu: Opet/PO/BP/TP bu durumdayken
        "stale price data" alarmı üretiliyordu.
        """
        code, alerts = self._run_main(
            [_price(changed_hours_ago=120, verified_hours_ago=1)]
        )

        self.assertEqual(code, 0, f"temiz rapor beklendi, alarmlar: {alerts}")
        self.assertEqual(alerts, [])

    def test_unverified_price_is_still_reported_stale(self):
        """Doğrulama izi de 5 günlükse alarm KORUNUR.

        Bu test olmadan 'düzeltme' alarmı tamamen kapatmak olurdu.
        """
        code, alerts = self._run_main(
            [_price(changed_hours_ago=120, verified_hours_ago=120)]
        )

        self.assertEqual(code, 1)
        self.assertTrue(
            any("stale price data" in a["message"] for a in alerts),
            f"bayatlık alarmı beklendi, gelen: {alerts}",
        )

    def test_missing_verification_falls_back_to_change_timestamp(self):
        """son_dogrulama boşsa (eski kayıt) son_guncelleme'ye düşülür."""
        code, alerts = self._run_main(
            [_price(changed_hours_ago=1, verified_hours_ago=None)]
        )

        self.assertEqual(code, 0, f"temiz rapor beklendi, alarmlar: {alerts}")
        self.assertEqual(alerts, [])

    def test_known_outage_brand_warns_without_blocking(self):
        """Kaynağı ölmüş markanın bayatlığı RAPORLANIR ama tek başına kırmızı
        yapmaz — rapor her 6 saatte bir kırmızı dönerse kırmızı anlamını
        yitirir ve bir sonraki GERÇEK arıza görünmez olur."""
        outage = known_outages.KnownOutage(
            bot="dummy_bot.py", brand=TEST_BRAND,
            url="https://example.invalid/prices", reason="kaynak emekliye ayrıldı",
            since=date(2026, 9, 9), review_by=date(2026, 10, 31),
        )
        with unittest.mock.patch.object(
            ops_report, "active_outage_for_brand",
            side_effect=lambda brand, today=None: outage if brand == TEST_BRAND else None,
        ):
            code, alerts = self._run_main(
                [_price(changed_hours_ago=120, verified_hours_ago=120)]
            )

        self.assertEqual(code, 0, f"bloklamaması beklendi, alarmlar: {alerts}")
        # Susturulmadı: alarm hâlâ açılıyor, sadece çıkış kodunu belirlemiyor.
        self.assertTrue(any("stale price data" in a["message"] for a in alerts))
        self.assertTrue(any(a["metadata"].get("known_outage") for a in alerts))

    def test_expired_outage_blocks_again(self):
        """Gözden geçirme tarihi geçmiş kayıt ayrıcalığını KAYBEDER."""
        with unittest.mock.patch.object(
            ops_report, "active_outage_for_brand", return_value=None
        ):
            code, alerts = self._run_main(
                [_price(changed_hours_ago=120, verified_hours_ago=120)]
            )
        self.assertEqual(code, 1)

    def test_unrelated_brand_failure_still_blocks_alongside_an_outage(self):
        """Bilinen arıza, BAŞKA bir markanın gerçek arızasını yutmamalı —
        mekanizmanın tek gerçek riski budur."""
        outage = known_outages.KnownOutage(
            bot="dummy_bot.py", brand="DeadBrand",
            url="https://example.invalid/prices", reason="kaynak emekliye ayrıldı",
            since=date(2026, 9, 9), review_by=date(2026, 10, 31),
        )
        alerts: list[dict] = []
        with unittest.mock.patch.object(ops_report, "supabase", unittest.mock.MagicMock()), \
             unittest.mock.patch.object(ops_report, "BRANDS", ["DeadBrand", TEST_BRAND]), \
             unittest.mock.patch.object(
                 ops_report, "_select_brand_stations", return_value=[_station()]), \
             unittest.mock.patch.object(
                 ops_report, "_select_prices",
                 return_value=[_price(changed_hours_ago=120, verified_hours_ago=120)]), \
             unittest.mock.patch.object(ops_report, "resolve_system_alerts"), \
             unittest.mock.patch.object(
                 ops_report, "active_outage_for_brand",
                 side_effect=lambda brand, today=None: outage if brand == "DeadBrand" else None), \
             unittest.mock.patch.object(
                 ops_report, "create_system_alert",
                 side_effect=lambda **kw: alerts.append(kw)):
            code = ops_report.main()

        self.assertEqual(code, 1, "sağlıklı markanın bayatlığı hâlâ bloklamalı")

    def test_price_query_requests_verification_column(self):
        """_select_prices son_dogrulama kolonunu gerçekten istemeli.

        Kolon sorgudan düşerse her satırda None gelir, mantık sessizce
        son_guncelleme fallback'ine düşer ve arıza aynen geri gelir.
        """
        fake = unittest.mock.MagicMock()
        fake.table.return_value.select.return_value.in_.return_value \
            .execute.return_value.data = []

        with unittest.mock.patch.object(ops_report, "supabase", fake):
            ops_report._select_prices(["st_1"])

        selected = fake.table.return_value.select.call_args[0][0]
        self.assertIn("son_dogrulama", selected)


class OpsReportVisibilityTest(unittest.TestCase):
    """§D-7: rapor KULLANICI gerçeğini mi söylüyor, veritabanı gerçeğini mi.

    Üretimdeki arıza: rapor yalnızca `aktif=true` sayıyordu. Shell kaynağı
    9 Eylül'de ölünce cron 1309 istasyonu `hidden` yaptı, ama rapor 33 gün
    boyunca "Total active stations: 6992" yazdı. Ürünün beşte biri
    karanlıktayken tek özet sayı sakin görünüyordu — kör noktanın bedeli
    bu sessizlikti.
    """

    _run_main = OpsReportFreshnessTest._run_main

    def _fresh_price(self) -> dict:
        return _price(changed_hours_ago=1, verified_hours_ago=1)

    def test_tam_karartma_uyari_uretir(self):
        """Marka aktif ama TEK bir istasyonu görünmüyorsa alarm şart."""
        code, alerts = self._run_main(
            [self._fresh_price()],
            stations=[_station(visibility="hidden")],
        )

        self.assertEqual(code, 1, "tam karartma bloklamalı")
        self.assertTrue(
            any("no user-visible stations" in a["message"] for a in alerts),
            f"karartma alarmı beklendi, gelen: {alerts}",
        )

    def test_kismi_karartma_uyari_URETMEZ(self):
        """Tek tek istasyonların gizlenmesi olağan dalgalanma.

        Her koşuda uyarı basmak S0-4'teki sahte "stale" gürültüsünü yeniden
        kurardı: sinyal anlamını yitirir ve sıradaki GERÇEK arıza görünmez olur.
        Kısmi fark "Shown" sütununda ve toplam satırında zaten görünüyor.
        """
        code, alerts = self._run_main(
            [self._fresh_price()],
            stations=[
                _station(visibility="visible", station_id="st_1"),
                _station(visibility="hidden", station_id="st_2"),
            ],
        )

        self.assertEqual(code, 0, f"kısmi karartma bloklamamalı, alarmlar: {alerts}")
        self.assertEqual(alerts, [])

    def test_low_priority_kullaniciya_GORUNUR_sayilir(self):
        """RLS `low_priority`'yi anon'a açıyor; rapor da öyle saymalı.

        Allowlist'in RLS'ten sapması, kör noktayı ters yönden geri getirirdi.
        """
        code, alerts = self._run_main(
            [self._fresh_price()],
            stations=[_station(visibility="low_priority")],
        )

        self.assertEqual(code, 0, f"low_priority görünür sayılmalı, alarmlar: {alerts}")
        self.assertEqual(alerts, [])

    def test_karartma_bilinen_arizayla_bloklamaz(self):
        """Shell'in bugünkü hâli: karartma RAPORLANIR ama kırmızı yapmaz.

        Kayıt 31 Ekim'de dolduğunda ayrıcalık kendiliğinden biter ve marka
        yeniden bloklayıcı olur — aşağıdaki test onu kilitliyor.
        """
        outage = known_outages.KnownOutage(
            bot="dummy_bot.py", brand=TEST_BRAND,
            url="https://example.invalid/prices", reason="kaynak emekliye ayrıldı",
            since=date(2026, 9, 9), review_by=date(2026, 10, 31),
        )
        with unittest.mock.patch.object(
            ops_report, "active_outage_for_brand",
            side_effect=lambda brand, today=None: outage if brand == TEST_BRAND else None,
        ):
            code, alerts = self._run_main(
                [self._fresh_price()],
                stations=[_station(visibility="hidden")],
            )

        self.assertEqual(code, 0, f"bloklamaması beklendi, alarmlar: {alerts}")
        # Susturulmadı: alarm açılıyor, sadece çıkış kodunu belirlemiyor.
        self.assertTrue(any("no user-visible stations" in a["message"] for a in alerts))
        self.assertTrue(any(a["metadata"].get("known_outage") for a in alerts))

    def test_suresi_dolmus_kayit_karartmayi_yeniden_bloklar(self):
        with unittest.mock.patch.object(
            ops_report, "active_outage_for_brand", return_value=None
        ):
            code, _ = self._run_main(
                [self._fresh_price()],
                stations=[_station(visibility="hidden")],
            )
        self.assertEqual(code, 1)

    def test_istasyon_sorgusu_visibility_status_kolonunu_ISTER(self):
        """Kolon sorgudan düşerse her satır None gelir, allowlist hiçbir
        satırı tutmaz ve rapor TÜM markaları karanlık sanır. Sorgunun kolonu
        gerçekten istediğini kilitlemek, mantığı kilitlemek kadar önemli."""
        fake = unittest.mock.MagicMock()
        fake.table.return_value.select.return_value.eq.return_value \
            .order.return_value.range.return_value.execute.return_value.data = []

        with unittest.mock.patch.object(ops_report, "supabase", fake):
            ops_report._select_brand_stations(TEST_BRAND)

        selected = fake.table.return_value.select.call_args[0][0]
        self.assertIn("visibility_status", selected)

    def test_allowlist_RLS_politikasiyla_ayni(self):
        """Tek tanım kaynağı kontrolü: sapma olursa burada yakalanır."""
        self.assertEqual(
            ops_report.USER_VISIBLE_STATUSES,
            frozenset({"visible", "low_priority"}),
        )


if __name__ == "__main__":
    unittest.main()
