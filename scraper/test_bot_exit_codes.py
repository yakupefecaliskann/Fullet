import contextlib
import io
import unittest

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


if __name__ == "__main__":
    unittest.main()
