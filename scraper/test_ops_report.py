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
from datetime import datetime, timedelta, timezone

import ops_report

VERIFIED_SOURCE = "api.opet.com.tr/api/fuelprices/allprices"
# MIN_ACTIVE_STATIONS / MIN_PRICE_ROWS bu markayı tanımıyor; .get(brand, 1)
# ile eşikler 1'e düşer, böylece testler sayı eşiklerine değil yalnızca
# tazeliğe bakar.
TEST_BRAND = "TestBrand"


def _iso(*, hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def _station() -> dict:
    return {
        "id": "st_1",
        "marka": TEST_BRAND,
        "il": "ISTANBUL",
        "aktif": True,
        "veri_kaynagi": VERIFIED_SOURCE,
        "guncellenme_tarihi": _iso(hours_ago=1),
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
    def _run_main(self, prices: list[dict]):
        """main()'i tek markalı sahte veriyle koşturur, (kod, alarmlar) döner."""
        alerts: list[dict] = []
        with unittest.mock.patch.object(ops_report, "supabase", unittest.mock.MagicMock()), \
             unittest.mock.patch.object(ops_report, "BRANDS", [TEST_BRAND]), \
             unittest.mock.patch.object(
                 ops_report, "_select_brand_stations", return_value=[_station()]), \
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


if __name__ == "__main__":
    unittest.main()
