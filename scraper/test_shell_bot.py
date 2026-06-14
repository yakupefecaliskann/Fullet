import unittest

from shell_bot import _prices_from_row


class ShellParserTest(unittest.TestCase):
    def test_shell_motorin_prefers_standard_diesel_over_premium_column(self):
        cols = [
            "",
            "",
            "BEYLIKDÜZÜ",
            "64,47",
            "65,02",
            "67,46",
            "71,77",
            "",
            "",
            "",
            "35,02",
            "",
            "35,02",
        ]

        self.assertEqual(_prices_from_row(cols)["Motorin"], 67.46)


if __name__ == "__main__":
    unittest.main()
