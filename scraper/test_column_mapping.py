import unittest

from column_mapping import (
    first_price_in_cell,
    prices_from_row,
    resolve_fuel_columns,
)

# Aşağıdaki başlıklar 1-2 Ağustos 2026'da canlı kaynaklardan alındı.
PO_HEADERS = [
    "Şehir", "V/Max Kurşunsuz 95", "V/Max Diesel", "Gazyağı",
    "Kalorifer Yakıtı", "Fuel Oil", "PO/gaz Otogaz",
]
BP_HEADERS = [
    "Şehir", "BP Kurşunsuz", "BP Ultimate Kurşunsuz", "BP Diesel",
    "BP Ultimate Diesel", "Gazyağı", "Kalorifer Yakıtı", "Fuel Oil",
    "Otogaz", "Yüksek Kükürtlü Fuel Oil",
]
TP_HEADERS = [
    "İLÇE", "KURŞUNSUZ BENZİN (TL/LT)", "GAZ YAĞI (TL/LT)", "MOTORİN (TL/LT)",
    "MOTORİN (TL/LT)", "KALORİFER YAKITI (TL/KG)", "FUEL OIL (TL/KG)",
    "Y.K. FUEL OIL (TL/KG)", "GAZ",
]


class ResolveFuelColumnsTest(unittest.TestCase):
    def test_petrol_ofisi_headers(self):
        self.assertEqual(
            resolve_fuel_columns(PO_HEADERS),
            {"Kursunsuz 95": [1], "Motorin": [2], "LPG": [6]},
        )

    def test_bp_headers_prefer_standard_over_ultimate(self):
        resolved = resolve_fuel_columns(BP_HEADERS)
        self.assertEqual(resolved["Kursunsuz 95"], [1, 2])
        self.assertEqual(resolved["Motorin"], [3, 4])
        self.assertEqual(resolved["LPG"], [8])

    def test_turkiye_petrolleri_headers(self):
        resolved = resolve_fuel_columns(TP_HEADERS)
        self.assertEqual(resolved["Kursunsuz 95"], [1])
        self.assertEqual(resolved["Motorin"], [3, 4])
        # Belirsiz "GAZ" başlığı LPG'ye eşleşmemeli — tahmin yerine boş bırak.
        self.assertNotIn("LPG", resolved)

    def test_kilogram_priced_columns_are_rejected(self):
        resolved = resolve_fuel_columns(["İl", "Otogaz (TL/Kg)", "Otogaz (TL/Lt)"])
        self.assertEqual(resolved["LPG"], [2])

    def test_kerosene_is_not_lpg(self):
        # "Gaz Yağı" yakıt kolonu değildir; bare "gaz" LPG'ye eşleşmemeli.
        self.assertEqual(resolve_fuel_columns(["İl", "Gaz Yağı (TL/Lt)"]), {})

    def test_unmatched_headers_yield_empty_map(self):
        self.assertEqual(resolve_fuel_columns(["Şehir", "Tarih", ""]), {})


class FirstPriceInCellTest(unittest.TestCase):
    def test_kdv_dahil_price_is_taken_first(self):
        # Petrol Ofisi/BP hücresi hem KDV dahil hem hariç fiyat taşır;
        # pompada ödenen tutar ilkidir.
        self.assertEqual(first_price_in_cell("67.18 55.99 TL/LT +KDV"), 67.18)

    def test_comma_decimal_with_three_digits(self):
        self.assertEqual(first_price_in_cell("68,140"), 68.14)

    def test_dash_and_empty_are_none(self):
        self.assertIsNone(first_price_in_cell("-"))
        self.assertIsNone(first_price_in_cell(""))
        self.assertIsNone(first_price_in_cell(None))

    def test_header_text_digits_are_not_prices(self):
        self.assertIsNone(first_price_in_cell("Kurşunsuz 95 Oktan"))


class PricesFromRowTest(unittest.TestCase):
    def test_fallback_stays_within_the_same_fuel(self):
        """Boş bir hücre asla BAŞKA bir ürünün fiyatını okutmamalı."""
        headers = ["İl", "Motorin Standart", "Motorin Premium", "Otogaz"]
        column_map = resolve_fuel_columns(headers)
        prices = prices_from_row(["ADANA", "-", "84,00", "-"], column_map)
        self.assertEqual(prices, {"Motorin": 84.00})

    def test_missing_fuel_column_is_simply_absent(self):
        column_map = resolve_fuel_columns(["İl", "Kurşunsuz 95"])
        self.assertEqual(
            prices_from_row(["ADANA", "68,91"], column_map),
            {"Kursunsuz 95": 68.91},
        )


if __name__ == "__main__":
    unittest.main()
