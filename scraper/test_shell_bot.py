import unittest

from column_mapping import resolve_fuel_columns
from shell_bot import _prices_from_row

# turkiyeshell.com/pompatest/History.aspx grid'inin canlı başlıkları
# (1 Ağustos 2026'da doğrulandı).
SHELL_HEADERS = [
    "Tarih",
    "İl",
    "İlçe",
    "K.Benzin 95 Oktan (TL/Lt) Shell Fuelsave",
    "K.Benzin 95 Oktan (TL/Lt) Shell V-Power",
    "Motorin (TL/Lt) Shell Fuelsave Diesel",
    "Motorin (TL/Lt) Shell V-Power Diesel",
    "VP Diesel +GTL (Motorin) (TL/Lt)",
    "Gaz Yagı (TL/Lt)",
    "Kalyak (TL/Kg)",
    "Yüksek Kükürtlü Fuel Oil (TL/Kg)",
    "Fuel Oil (TL/Kg)",
    "Otogaz (TL/Lt) Shell Autogas LPG",
]


class ShellColumnMapTest(unittest.TestCase):
    def setUp(self):
        self.column_map = resolve_fuel_columns(SHELL_HEADERS)

    def test_otogaz_column_is_resolved_from_header(self):
        self.assertEqual(self.column_map["LPG"], [12])

    def test_weight_priced_columns_are_never_fuel_columns(self):
        """Kalyak / Fuel Oil / Y.K. Fuel Oil (TL/Kg) hiçbir yakıta eşleşmemeli."""
        for indices in self.column_map.values():
            self.assertNotIn(9, indices)
            self.assertNotIn(10, indices)
            self.assertNotIn(11, indices)

    def test_standard_columns_are_preferred_over_premium(self):
        # Fuelsave (standart) V-Power'dan (premium) önce denenmeli.
        self.assertEqual(self.column_map["Kursunsuz 95"][0], 3)
        self.assertEqual(self.column_map["Motorin"][0], 5)


class ShellRowParsingTest(unittest.TestCase):
    def setUp(self):
        self.column_map = resolve_fuel_columns(SHELL_HEADERS)

    def test_empty_otogaz_never_falls_back_to_fuel_oil(self):
        """Yol haritası S1-1 regresyon kilidi.

        Otogaz kolonu "-" iken eski kod `or _price_at(cols, 10)` ile
        "Yüksek Kükürtlü Fuel Oil (TL/Kg)" değerini (38,51) LPG diye
        yazıyordu. Artık LPG hiç üretilmemeli.
        """
        row = ["01.08.2026", "ANKARA", "CANKAYA", "-", "68,140", "-", "82,080",
               "-", "82,620", "64,880", "38,510", "46,770", "-"]
        prices = _prices_from_row(row, self.column_map)
        self.assertNotIn("LPG", prices)
        self.assertEqual(prices["Kursunsuz 95"], 68.14)
        self.assertEqual(prices["Motorin"], 82.08)

    def test_real_otogaz_value_is_used_when_present(self):
        row = ["01.08.2026", "X", "Y", "-", "68,140", "-", "82,080",
               "-", "82,620", "64,880", "38,510", "46,770", "31,490"]
        prices = _prices_from_row(row, self.column_map)
        self.assertEqual(prices["LPG"], 31.49)

    def test_shell_motorin_prefers_standard_diesel_over_premium_column(self):
        cols = ["", "", "BEYLIKDÜZÜ", "64,47", "65,02", "67,46", "71,77",
                "", "", "", "35,02", "", "35,02"]
        prices = _prices_from_row(cols, self.column_map)
        self.assertEqual(prices["Motorin"], 67.46)
        self.assertEqual(prices["Kursunsuz 95"], 64.47)
        # Kolon 10 (Y.K. Fuel Oil) dolu olsa bile LPG kolon 12'den okunur.
        self.assertEqual(prices["LPG"], 35.02)


if __name__ == "__main__":
    unittest.main()
