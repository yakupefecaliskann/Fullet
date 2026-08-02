import contextlib
import io
import unittest

from db_utils import finish_bot_run
from models import SaveSummary
from run_all_bots import _parse_scraped_records


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


if __name__ == "__main__":
    unittest.main()
