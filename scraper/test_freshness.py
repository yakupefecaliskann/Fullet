import unittest
import unittest.mock
from datetime import timedelta

from freshness import (
    FRESH_MAX_HOURS,
    STALE_MAX_HOURS,
    needs_verification_write,
    now_utc,
    status_for_age,
)


class StatusForAgeTest(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(status_for_age(0), "fresh")
        self.assertEqual(status_for_age(FRESH_MAX_HOURS), "fresh")
        self.assertEqual(status_for_age(FRESH_MAX_HOURS + 0.1), "stale")
        self.assertEqual(status_for_age(STALE_MAX_HOURS), "stale")
        self.assertEqual(status_for_age(STALE_MAX_HOURS + 0.1), "unknown")
        self.assertEqual(status_for_age(None), "unknown")


class NeedsVerificationWriteTest(unittest.TestCase):
    def setUp(self):
        self.now = now_utc()

    def _ago(self, hours):
        return (self.now - timedelta(hours=hours)).isoformat()

    def test_stale_row_always_gets_a_verification_write(self):
        self.assertTrue(
            needs_verification_write(self._ago(0.1), "stale", reference=self.now)
        )

    def test_recently_verified_fresh_row_is_debounced(self):
        self.assertFalse(
            needs_verification_write(self._ago(0.2), "fresh", reference=self.now)
        )

    def test_fresh_row_past_debounce_is_rewritten(self):
        """Yol haritası S0-3 regresyon kilidi.

        Eski kod 24 saatten yeni + fresh satırları tamamen atlıyordu; 12
        saatlik pg_cron eşiği DOĞRU fiyatı bayat işaretliyordu. 6 saatlik
        bot cadence'inde doğrulama izi her koşuda yazılmalı.
        """
        self.assertTrue(
            needs_verification_write(self._ago(6), "fresh", reference=self.now)
        )

    def test_missing_timestamp_is_rewritten(self):
        self.assertTrue(needs_verification_write(None, "fresh", reference=self.now))

    def test_debounce_is_shorter_than_bot_cadence(self):
        # Botlar 6 saatte bir koşuyor; debounce bundan küçük olmazsa
        # doğrulama izi yine atlanır ve S0-3 döngüsü geri döner.
        from freshness import VERIFY_DEBOUNCE_HOURS
        self.assertLess(VERIFY_DEBOUNCE_HOURS, 6)
        self.assertLess(VERIFY_DEBOUNCE_HOURS, FRESH_MAX_HOURS)


class BulkUpsertVerificationTest(unittest.TestCase):
    """`_bulk_upsert_prices`'ın iki yazma yolunu ayırt ettiğini doğrular."""

    def _mock_existing(self, mock_supabase, *, fiyat, status, verified_hours_ago):
        response = unittest.mock.MagicMock()
        response.data = [{
            "istasyon_id": "st_1",
            "yakit_tipi": "Motorin",
            "fiyat": fiyat,
            "price_status": status,
            "son_guncelleme": (now_utc() - timedelta(days=30)).isoformat(),
            "son_dogrulama": (now_utc() - timedelta(hours=verified_hours_ago)).isoformat(),
        }]
        table = unittest.mock.MagicMock()
        mock_supabase.table.return_value = table
        table.select.return_value.in_.return_value.execute.return_value = response
        return table

    @unittest.mock.patch("database_writes.supabase")
    def test_unchanged_price_writes_only_the_verification_trail(self, mock_supabase):
        table = self._mock_existing(
            mock_supabase, fiyat=40.0, status="fresh", verified_hours_ago=6
        )
        from database_writes import _bulk_upsert_prices

        touched = _bulk_upsert_prices(
            [{"istasyon_id": "st_1", "yakit_tipi": "Motorin", "fiyat": 40.0}]
        )

        self.assertEqual(touched, 1)
        # Fiyat yazılmadı -> trigger tetiklenmez, son_guncelleme korunur.
        table.upsert.assert_not_called()
        table.update.assert_called_once()
        payload = table.update.call_args[0][0]
        self.assertEqual(payload["price_status"], "fresh")
        self.assertIn("son_dogrulama", payload)
        self.assertNotIn("fiyat", payload)
        self.assertNotIn("son_guncelleme", payload)

    @unittest.mock.patch("database_writes.supabase")
    def test_changed_price_does_a_full_upsert(self, mock_supabase):
        table = self._mock_existing(
            mock_supabase, fiyat=40.0, status="fresh", verified_hours_ago=6
        )
        from database_writes import _bulk_upsert_prices

        touched = _bulk_upsert_prices(
            [{"istasyon_id": "st_1", "yakit_tipi": "Motorin", "fiyat": 41.0}]
        )

        self.assertEqual(touched, 1)
        table.upsert.assert_called_once()
        written = table.upsert.call_args[0][0][0]
        self.assertEqual(written["fiyat"], 41.0)
        self.assertEqual(written["price_status"], "fresh")
        self.assertIn("son_dogrulama", written)

    @unittest.mock.patch("database_writes.supabase")
    def test_stale_row_is_refreshed_even_when_price_is_unchanged(self, mock_supabase):
        table = self._mock_existing(
            mock_supabase, fiyat=40.0, status="stale", verified_hours_ago=0.1
        )
        from database_writes import _bulk_upsert_prices

        touched = _bulk_upsert_prices(
            [{"istasyon_id": "st_1", "yakit_tipi": "Motorin", "fiyat": 40.0}]
        )

        self.assertEqual(touched, 1)
        table.update.assert_called_once()
        self.assertEqual(table.update.call_args[0][0]["price_status"], "fresh")


if __name__ == "__main__":
    unittest.main()
