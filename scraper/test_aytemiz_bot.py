import unittest

from bs4 import BeautifulSoup

import aytemiz_bot


class AytemizParserTest(unittest.TestCase):
    def test_parse_table_rows_uses_only_pump_fuel_columns(self):
        soup = BeautifulSoup(
            """
            <table>
              <tr>
                <th>Il</th>
                <th>Benzin</th>
                <th>Motorin</th>
                <th>Motorin Optimum</th>
                <th>Kalorifer Yakiti</th>
                <th>Fuel Oil</th>
              </tr>
              <tr>
                <td>Adana</td>
                <td>66,25</td>
                <td>73,61</td>
                <td>73,61</td>
                <td>58,28</td>
                <td>46,02</td>
              </tr>
            </table>
            """,
            "html.parser",
        )

        rows = list(aytemiz_bot._parse_table_rows(soup))

        self.assertEqual(rows, [["Adana", "66,25", "73,61"]])


if __name__ == "__main__":
    unittest.main()
