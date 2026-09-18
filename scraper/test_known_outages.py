"""Bilinen kaynak arızası mekanizmasının regresyon kilidi.

Bu testlerin varlık sebebi, mekanizmanın KÖTÜYE gidebileceği üç yol:
  1. Parser kırıklığını da susturmaya başlaması,
  2. Süresi dolduğu hâlde susturmaya devam etmesi,
  3. Kaynak geri döndükten sonra kaydın sessizce yerinde kalması.
Üçü de mekanizmayı `TOLERATED_FAILURE_BOTS`'un kaldırılma sebebine geri
çevirirdi. Aşağıdaki testler üçünü de kilitler.
"""

import contextlib
import io
import unittest
import unittest.mock
from datetime import date, datetime, timezone

import known_outages
import run_all_bots
from db_utils import finish_bot_run
from known_outages import (
    EXIT_SOURCE_GONE,
    KNOWN_OUTAGES,
    KnownOutage,
    active_outage_for_bot,
    active_outage_for_brand,
    outage_for_bot,
)
from models import SaveSummary


def _outage(**overrides) -> KnownOutage:
    defaults = dict(
        bot="dummy_bot.py",
        brand="Dummy",
        url="https://example.invalid/prices",
        reason="test",
        since=date(2026, 9, 9),
        review_by=date(2026, 10, 31),
    )
    defaults.update(overrides)
    return KnownOutage(**defaults)


class ExitCodeContractTest(unittest.TestCase):
    """`source_gone`, 'parser kırık' ile 'kaynak yok'u AYIRMALI."""

    def test_source_gone_returns_its_own_exit_code(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = finish_bot_run(
                "dummy_bot.py",
                scraped=0,
                summary=SaveSummary(),
                targets_ok=0,
                targets_total=280,
                source_gone=True,
            )
        self.assertEqual(code, EXIT_SOURCE_GONE)
        self.assertNotEqual(EXIT_SOURCE_GONE, 1)
        self.assertIn("[KAYNAK-YOK]", buffer.getvalue())

    def test_source_gone_still_reports_honest_coverage(self):
        # Kapsama satırı düşerse "hiçbir hedef tazelenmedi" bilgisi kaybolur
        # ve arıza telemetride 0/0 olarak görünmez hâle gelir.
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            finish_bot_run(
                "dummy_bot.py",
                scraped=0,
                summary=SaveSummary(),
                targets_ok=0,
                targets_total=280,
                source_gone=True,
            )
        self.assertIn("targets_ok=0 targets_total=280", buffer.getvalue())

    def test_broken_parser_is_not_disguised_as_a_dead_source(self):
        """Kaynak ayakta ama 0 kayıt geldiyse çıkış kodu 1 KALMALI."""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = finish_bot_run("dummy_bot.py", scraped=0, summary=SaveSummary())
        self.assertEqual(code, 1)


class ShellBotWiringTest(unittest.TestCase):
    """`source_dead` -> `source_gone` kablosu kopmamalı.

    Bu tek parametre kopsa mekanizmanın geri kalanı kusursuz çalışır ve yine de
    hiçbir işe yaramaz: bot exit 1 döner, orkestratör "parser kırık" sanır,
    pipeline kalıcı kırmızıya geri döner."""

    def _run_main(self, *, source_dead, scraped):
        import shell_bot

        stats = {"planned": 280, "attempted": 0, "ok": 0, "missing": 0,
                 "failed": 0, "budget_exhausted": False, "source_dead": source_dead}
        data = [{"marka": "Shell"}] * scraped
        with unittest.mock.patch.object(
            shell_bot, "scrape_shell_data", return_value=(data, stats)
        ), unittest.mock.patch.object(
            shell_bot, "save_regional_prices_to_supabase", return_value=SaveSummary()
        ), contextlib.redirect_stdout(io.StringIO()):
            return shell_bot.main()

    def test_dead_source_exits_with_source_gone_code(self):
        self.assertEqual(self._run_main(source_dead=True, scraped=0), EXIT_SOURCE_GONE)

    def test_zero_records_with_live_source_still_exits_one(self):
        self.assertEqual(self._run_main(source_dead=False, scraped=0), 1)

    def test_successful_run_exits_zero(self):
        self.assertEqual(self._run_main(source_dead=False, scraped=280), 0)


class ExpiryTest(unittest.TestCase):
    """Kayıt kalıcı bir göz bağına dönüşememeli."""

    def test_active_before_review_date(self):
        outage = _outage(review_by=date(2026, 10, 31))
        self.assertFalse(outage.is_expired(date(2026, 10, 30)))
        self.assertFalse(outage.is_expired(date(2026, 10, 31)))

    def test_expired_after_review_date(self):
        outage = _outage(review_by=date(2026, 10, 31))
        self.assertTrue(outage.is_expired(date(2026, 11, 1)))

    def test_expired_record_stops_suppressing(self):
        expired = _outage(bot="dummy_bot.py", review_by=date(2020, 1, 1))
        with unittest.mock.patch.object(known_outages, "KNOWN_OUTAGES", (expired,)):
            # Kayıt hâlâ BULUNUR (sağlık kontrolü sebebi yazabilsin diye)...
            self.assertIsNotNone(outage_for_bot("dummy_bot.py"))
            # ...ama artık susturma YETKİSİ yoktur.
            self.assertIsNone(active_outage_for_bot("dummy_bot.py"))
            self.assertIsNone(active_outage_for_brand("Dummy"))

    def test_describe_names_the_expiry(self):
        expired = _outage(review_by=date(2026, 10, 31))
        self.assertIn("GEÇTİ", expired.describe(date(2026, 11, 5)))
        self.assertIn("gün kaldı", expired.describe(date(2026, 10, 1)))


class OrchestratorOutcomeTest(unittest.TestCase):
    """EXIT_SOURCE_GONE yalnızca GEÇERLİ bir kayıt varsa hoş görülür."""

    def _run_once(self, returncode, outage):
        completed = unittest.mock.Mock(
            returncode=returncode,
            stdout="[RECORDS] scraped=0 stations=0 prices=0 targets_ok=0 targets_total=280\n",
            stderr="",
        )
        buffer = io.StringIO()
        with unittest.mock.patch.object(run_all_bots.subprocess, "run", return_value=completed), \
             unittest.mock.patch.object(run_all_bots, "active_outage_for_bot", return_value=outage), \
             unittest.mock.patch.object(run_all_bots, "record_bot_run") as record, \
             contextlib.redirect_stdout(buffer):
            outcome = run_all_bots._run_subprocess_once(
                "dummy_bot.py", None, 60, "prices"
            )
        return outcome, record, buffer.getvalue()

    def test_acknowledged_dead_source_is_skipped_not_failed(self):
        outcome, record, output = self._run_once(EXIT_SOURCE_GONE, _outage())
        self.assertEqual(outcome, run_all_bots.OUTCOME_OUTAGE)
        self.assertEqual(record.call_args.kwargs["status"], "skipped")
        # Tırmandırma kapalı: kalıcı `critical` alarm üretilmemeli.
        self.assertFalse(record.call_args.kwargs["escalate_failures"])
        self.assertIn("[BILINEN-ARIZA]", output)

    def test_unacknowledged_dead_source_is_a_hard_failure(self):
        """Kaydı olmayan (ya da süresi dolmuş) ölü kaynak HABERDİR."""
        outcome, record, output = self._run_once(EXIT_SOURCE_GONE, None)
        self.assertEqual(outcome, run_all_bots.OUTCOME_FAILED)
        self.assertEqual(record.call_args.kwargs["status"], "failed")
        self.assertIn("known_outages.py", output)

    def test_ordinary_failure_is_untouched_by_the_mechanism(self):
        outcome, record, _ = self._run_once(1, _outage())
        self.assertEqual(outcome, run_all_bots.OUTCOME_FAILED)
        self.assertEqual(record.call_args.kwargs["status"], "failed")
        self.assertTrue(record.call_args.kwargs.get("escalate_failures", True))

    def test_dead_source_is_not_retried(self):
        """404'ü ikinci kez sormanın tek kazandığı günlüğü ikiye katlamak."""
        calls = []

        def fake_once(*args, **kwargs):
            calls.append(args)
            return run_all_bots.OUTCOME_OUTAGE

        with unittest.mock.patch.object(run_all_bots, "_run_subprocess_once", fake_once), \
             unittest.mock.patch.object(run_all_bots, "active_outage_for_bot", return_value=_outage()), \
             unittest.mock.patch.object(run_all_bots, "create_system_alert"), \
             unittest.mock.patch.object(run_all_bots, "resolve_system_alerts"), \
             contextlib.redirect_stdout(io.StringIO()):
            outcome = run_all_bots.run_bot_with_retries("dummy_bot.py", mode="prices")
        self.assertEqual(outcome, run_all_bots.OUTCOME_OUTAGE)
        self.assertEqual(len(calls), 1)

    def test_outage_supersedes_the_old_critical_alerts(self):
        resolved, created = [], []
        with unittest.mock.patch.object(
            run_all_bots, "_run_subprocess_once", return_value=run_all_bots.OUTCOME_OUTAGE
        ), unittest.mock.patch.object(
            run_all_bots, "active_outage_for_bot", return_value=_outage()
        ), unittest.mock.patch.object(
            run_all_bots, "create_system_alert", side_effect=lambda **kw: created.append(kw)
        ), unittest.mock.patch.object(
            run_all_bots, "resolve_system_alerts", side_effect=lambda **kw: resolved.append(kw)
        ), contextlib.redirect_stdout(io.StringIO()):
            run_all_bots.run_bot_with_retries("dummy_bot.py", mode="prices")

        resolved_titles = {entry.get("title") for entry in resolved}
        self.assertIn("dummy_bot.py arka arkaya başarısız", resolved_titles)
        self.assertIn("dummy_bot.py failed", resolved_titles)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["severity"], "warning")

    def test_record_expiring_mid_run_fails_instead_of_crashing(self):
        """Koşu gece yarısını geçerse kayıt iki çağrı arasında süresini
        doldurabilir. Bir raporlama ayrıntısı uğruna orkestratör ölmemeli."""
        with unittest.mock.patch.object(
            run_all_bots, "_run_subprocess_once", return_value=run_all_bots.OUTCOME_OUTAGE
        ), unittest.mock.patch.object(
            run_all_bots, "active_outage_for_bot", return_value=None
        ), unittest.mock.patch.object(
            run_all_bots, "create_system_alert"
        ), unittest.mock.patch.object(
            run_all_bots, "resolve_system_alerts"
        ), contextlib.redirect_stdout(io.StringIO()):
            outcome = run_all_bots.run_bot_with_retries("dummy_bot.py", mode="prices")
        self.assertEqual(outcome, run_all_bots.OUTCOME_FAILED)

    def test_recovered_bot_closes_the_outage_alert(self):
        resolved = []
        with unittest.mock.patch.object(
            run_all_bots, "_run_subprocess_once", return_value=run_all_bots.OUTCOME_OK
        ), unittest.mock.patch.object(
            run_all_bots, "resolve_system_alerts", side_effect=lambda **kw: resolved.append(kw)
        ), contextlib.redirect_stdout(io.StringIO()):
            outcome = run_all_bots.run_bot_with_retries("dummy_bot.py", mode="prices")
        self.assertEqual(outcome, run_all_bots.OUTCOME_OK)
        self.assertIn(
            "dummy_bot.py kaynağı kapalı (bilinen arıza)",
            {entry.get("title") for entry in resolved},
        )


class HealthCheckSilenceTest(unittest.TestCase):
    """Sağlık kontrolünün sessiz-bot kararı."""

    def _levels(self, **kwargs):
        from backend_health_check import evaluate_bot_silence

        params = dict(
            yas=200.0,
            son_basari=datetime(2026, 9, 9, tzinfo=timezone.utc),
            warn_hours=12,
            fail_hours=24,
            outage=None,
        )
        params.update(kwargs)
        rows = evaluate_bot_silence("dummy_bot.py", **params)
        return [level for level, _, _ in rows], rows

    def test_silent_bot_without_record_fails(self):
        levels, _ = self._levels()
        self.assertEqual(levels, ["fail"])

    def test_silent_bot_with_active_record_only_warns(self):
        levels, rows = self._levels(outage=_outage())
        self.assertEqual(levels, ["warn"])
        self.assertIn("gözden geçirme", rows[0][2])

    def test_silent_bot_with_expired_record_fails_again(self):
        levels, rows = self._levels(outage=_outage(review_by=date(2020, 1, 1)))
        self.assertEqual(levels, ["fail"])
        self.assertIn("GEÇTİ", rows[0][2])

    def test_recovered_bot_with_lingering_record_demands_cleanup(self):
        levels, rows = self._levels(yas=1.0, outage=_outage())
        self.assertIn("fail", levels)
        self.assertIn("kaydı SİL", rows[0][2])

    def test_healthy_bot_without_record_is_ok(self):
        levels, _ = self._levels(yas=1.0)
        self.assertEqual(levels, ["ok"])

    def test_record_never_suppresses_an_unrelated_bot(self):
        """Kayıt bot adına bağlı; başka bir botun sessizliği etkilenmemeli."""
        self.assertIsNone(active_outage_for_bot("opet_bot.py"))


class RegistryIntegrityTest(unittest.TestCase):
    """Kayıt defterinin kendisi tutarlı kalmalı."""

    def test_every_record_has_a_review_date_after_its_start(self):
        for outage in KNOWN_OUTAGES:
            with self.subTest(bot=outage.bot):
                self.assertGreater(outage.review_by, outage.since)
                self.assertTrue(outage.reason.strip())
                self.assertTrue(outage.url.startswith("http"))

    def test_recorded_bots_actually_exist_in_the_rotation(self):
        """Kaydı olan bot rotasyondan çıkarılırsa kayıt ölü koda dönüşür —
        ve "kaynak geri döndü mü?" yoklaması da sessizce durur."""
        rotation = set(run_all_bots.PRICE_BOTS) | set(run_all_bots.STATION_BOTS) | {"news_bot.py"}
        for outage in KNOWN_OUTAGES:
            with self.subTest(bot=outage.bot):
                self.assertIn(outage.bot, rotation)


if __name__ == "__main__":
    unittest.main()
