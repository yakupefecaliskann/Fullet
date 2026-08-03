import contextlib
import io
import unittest
import unittest.mock
from datetime import datetime, timezone
from types import SimpleNamespace

from db_utils import MIN_TARGET_COVERAGE, finish_bot_run
from models import SaveSummary
from run_all_bots import _parse_scraped_records, _parse_target_coverage


class FinishBotRunTest(unittest.TestCase):
    """Faz 0 / S0-1: 'boş liste + exit 0' kombinasyonu bir daha yaşanmamalı."""

    def test_zero_scrape_returns_failure_exit_code(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = finish_bot_run("dummy_bot.py", scraped=0, summary=SaveSummary())
        self.assertEqual(code, 1)
        self.assertIn("[RECORDS] scraped=0", buffer.getvalue())
        self.assertIn("[FAIL]", buffer.getvalue())

    def test_nonzero_scrape_returns_success_exit_code(self):
        summary = SaveSummary(stations_touched=5, prices_touched=12)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = finish_bot_run("dummy_bot.py", scraped=81, summary=summary)
        self.assertEqual(code, 0)
        self.assertIn("[RECORDS] scraped=81 stations=5 prices=12", buffer.getvalue())

    def test_zero_written_with_nonzero_scrape_is_still_success(self):
        # Zero-cost diff: fiyatlar değişmediyse 0 yazım meşru bir başarıdır.
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = finish_bot_run("dummy_bot.py", scraped=81, summary=SaveSummary())
        self.assertEqual(code, 0)


class ParseScrapedRecordsTest(unittest.TestCase):
    """run_all_bots, bot stdout'undaki [RECORDS] satırını doğru parse etmeli."""

    def test_parses_records_line(self):
        stdout = "[INFO] something\n[RECORDS] scraped=81 stations=5 prices=12\n[OK] done\n"
        self.assertEqual(_parse_scraped_records(stdout), 81)

    def test_parses_zero(self):
        self.assertEqual(_parse_scraped_records("[RECORDS] scraped=0 stations=0 prices=0"), 0)

    def test_missing_line_returns_none(self):
        # Eski formatta çıktı veren bot 'bilinmiyor' kalmalı, 'empty' sayılmamalı.
        self.assertIsNone(_parse_scraped_records("[OK] finished in 3.1s."))

    def test_none_stdout_returns_none(self):
        self.assertIsNone(_parse_scraped_records(None))

    def test_line_must_start_at_column_zero(self):
        self.assertIsNone(_parse_scraped_records("gürültü [RECORDS] scraped=7"))


class TargetCoverageTest(unittest.TestCase):
    """Hedef bazlı kazımada 'çoğu hedefi kaybettim' sessiz kalmamalı.

    Faz 0 yalnızca 'hiç kayıt yok' durumunu görünür kılmıştı; shell_bot
    hedeflerinin %63'ünü kaybedip yine de yüzlerce kayıt döndürdüğü için
    'success' görünüyordu.
    """

    def test_records_line_carries_coverage(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            finish_bot_run(
                "shell_bot.py", scraped=534, summary=SaveSummary(1, 1),
                targets_ok=55, targets_total=150,
            )
        output = buffer.getvalue()
        self.assertIn("targets_ok=55 targets_total=150", output)
        self.assertIn("[DEGRADED]", output)

    def test_good_coverage_is_not_degraded(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = finish_bot_run(
                "shell_bot.py", scraped=534, summary=SaveSummary(1, 1),
                targets_ok=140, targets_total=150,
            )
        self.assertEqual(code, 0)
        self.assertNotIn("[DEGRADED]", buffer.getvalue())

    def test_low_coverage_still_exits_zero(self):
        # Kısmi veri doğrudur ve değerlidir; exit 1 kazımayı boşuna tekrarlar
        # ve pipeline'ı kalıcı kırmızıya boyar. Sinyal 'degraded' durumudur.
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = finish_bot_run(
                "shell_bot.py", scraped=534, summary=SaveSummary(1, 1),
                targets_ok=1, targets_total=150,
            )
        self.assertEqual(code, 0)

    def test_coverage_is_optional(self):
        # Bölgesel botlar tek sayfa okur; kapsama alanları basılmamalı.
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            finish_bot_run("opet_bot.py", scraped=81, summary=SaveSummary(1, 1))
        self.assertNotIn("targets_total", buffer.getvalue())
        self.assertNotIn("[COVERAGE]", buffer.getvalue())

    def test_parses_coverage_from_stdout(self):
        stdout = "[RECORDS] scraped=534 stations=3 prices=9 targets_ok=55 targets_total=150\n"
        self.assertEqual(_parse_target_coverage(stdout), (55, 150))

    def test_coverage_absent_returns_none(self):
        self.assertIsNone(
            _parse_target_coverage("[RECORDS] scraped=81 stations=5 prices=12")
        )

    def test_threshold_matches_live_failure(self):
        # 2 Ağustos canlı ölçümü: 150 hedeften ~55'i okunabiliyordu.
        self.assertLess(55 / 150, MIN_TARGET_COVERAGE)


class CoveragePersistedTest(unittest.TestCase):
    """Kapsama sayilari bot_runs KOLONUNA yazilmali (denetim bulgusu 2).

    stdout_excerpt'e guvenilemez: _compact_log ilk 4000 karakteri tutar,
    [RECORDS] satiri kosunun SONUNDA basilir. Canlida 20 shell_bot kaydinin
    hicbirinde kapsama satiri yoktu.
    """

    def _payload_for(self, **kwargs):
        import telemetry

        captured = {}

        class FakeQuery:
            def select(self, *a, **k):
                return self

            def eq(self, *a, **k):
                return self

            def order(self, *a, **k):
                return self

            def limit(self, *a, **k):
                return self

            def insert(self, payload, *a, **k):
                captured.update(payload)
                return self

            def execute(self):
                return SimpleNamespace(data=[])

        class FakeSupabase:
            def table(self, _name):
                return FakeQuery()

        now = datetime.now(timezone.utc)
        with unittest.mock.patch.object(telemetry, "supabase", FakeSupabase()), \
                unittest.mock.patch.object(telemetry, "create_system_alert", lambda **kw: None), \
                unittest.mock.patch.object(telemetry, "resolve_system_alerts", lambda **kw: None), \
                contextlib.redirect_stdout(io.StringIO()):
            telemetry.record_bot_run(
                bot_name="shell_bot.py", mode="prices", status="success",
                started_at=now, finished_at=now, **kwargs
            )
        return captured

    def test_coverage_written_on_successful_run(self):
        # Asil nokta: degraded OLMAYAN kosuda da kapsama saklanmali.
        p = self._payload_for(targets_ok=142, targets_total=150)
        self.assertEqual(p.get("targets_ok"), 142)
        self.assertEqual(p.get("targets_total"), 150)

    def test_non_target_bot_omits_columns(self):
        # opet/total/tp tek istekle tum ulkeyi ceker; 0 ile karistirilmamali.
        p = self._payload_for()
        self.assertNotIn("targets_ok", p)
        self.assertNotIn("targets_total", p)

    def test_zero_ok_is_recorded_not_dropped(self):
        p = self._payload_for(targets_ok=0, targets_total=150)
        self.assertEqual(p.get("targets_ok"), 0)
        self.assertEqual(p.get("targets_total"), 150)


class DegradedIsNotFailureTest(unittest.TestCase):
    """'degraded' ardışık-hata eskalasyonuna GİRMEMELİ.

    Canlı kanıt (Faz 0-2 denetimi): 2 Ağustos 23:00 ve 23:26'daki iki degraded
    Shell koşusu 23:11'de "shell_bot.py arka arkaya başarısız" başlıklı CRITICAL
    alarm açtı — oysa bot her iki koşuda da yüzlerce fiyat yazmıştı. degraded,
    tasarım gereği "veri yazıldı ama eksik" demek; başarısızlık değil.
    """

    def _record(self, status, previous_statuses):
        import telemetry

        calls = {"alert": [], "resolve": []}

        class FakeQuery:
            def select(self, *a, **k):
                return self

            def eq(self, *a, **k):
                return self

            def order(self, *a, **k):
                return self

            def limit(self, *a, **k):
                return self

            def insert(self, *a, **k):
                return self

            def execute(self):
                return SimpleNamespace(
                    data=[{"status": s, "started_at": "2026-08-02T23:00:00Z"}
                          for s in previous_statuses]
                )

        class FakeSupabase:
            def table(self, _name):
                return FakeQuery()

        now = datetime.now(timezone.utc)
        with unittest.mock.patch.object(telemetry, "supabase", FakeSupabase()), \
                unittest.mock.patch.object(
                    telemetry, "create_system_alert",
                    lambda **kw: calls["alert"].append(kw)), \
                unittest.mock.patch.object(
                    telemetry, "resolve_system_alerts",
                    lambda **kw: calls["resolve"].append(kw)), \
                contextlib.redirect_stdout(io.StringIO()):
            telemetry.record_bot_run(
                bot_name="shell_bot.py",
                mode="prices",
                status=status,
                started_at=now,
                finished_at=now,
            )
        return calls

    def test_consecutive_degraded_does_not_raise_critical(self):
        calls = self._record("degraded", ["degraded", "degraded"])
        self.assertEqual(calls["alert"], [], "degraded critical alarm açmamalı")

    def test_degraded_resolves_stale_failure_alarm(self):
        # Bot yaşıyor ve yazıyor: eski ardışık-hata alarmı kapanmalı.
        calls = self._record("degraded", ["failed", "failed"])
        self.assertEqual(len(calls["resolve"]), 1)

    def test_degraded_breaks_a_failure_streak(self):
        # failed -> degraded -> failed ardışık DEĞİLDİR; seri degraded'da kırılır.
        calls = self._record("failed", ["degraded", "failed"])
        self.assertEqual(calls["alert"], [])

    def test_real_failures_still_escalate(self):
        # Regresyon koruması: düzeltme alarmı tamamen sağır etmemeli.
        calls = self._record("failed", ["failed", "success"])
        self.assertEqual(len(calls["alert"]), 1)
        self.assertEqual(calls["alert"][0]["severity"], "critical")


if __name__ == "__main__":
    unittest.main()
