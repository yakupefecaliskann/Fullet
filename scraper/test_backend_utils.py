import os
import unittest

import db_utils


class BackendUtilsTest(unittest.TestCase):
    def test_parse_price_accepts_turkish_and_dot_decimal(self):
        self.assertEqual(db_utils.parse_price("65,68 TL"), 65.68)
        self.assertEqual(db_utils.parse_price("65.68"), 65.68)
        self.assertEqual(db_utils.parse_price("1.265,80"), None)
        self.assertIsNone(db_utils.parse_price("-"))

    def test_parse_coordinate_preserves_precision(self):
        self.assertEqual(db_utils.parse_coordinate("41.028617", latitude=True), 41.028617)
        self.assertEqual(db_utils.parse_coordinate("28,936964", latitude=False), 28.936964)
        self.assertIsNone(db_utils.parse_coordinate("370434200", latitude=True))

    def test_normalize_scraped_data_keeps_only_valid_items(self):
        data, skipped = db_utils.normalize_scraped_data([
            {
                "marka": "Opet",
                "istasyon_adi": "Opet Test Istasyonu",
                "il": "Istanbul / Anadolu",
                "ilce": "",
                "enlem": "41.01",
                "boylam": "29.01",
                "fiyatlar": {"Benzin": "63,50", "Motorin": "70.10", "LPG": "-"},
            },
            {"marka": "Opet", "il": "", "fiyatlar": {"Benzin": "63,50"}},
        ])

        self.assertEqual(skipped, 1)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["il"], "ISTANBUL")
        self.assertEqual(data[0]["fiyatlar"]["Kursunsuz 95"], 63.50)
        self.assertEqual(data[0]["fiyatlar"]["Motorin"], 70.10)
        self.assertNotIn("LPG", data[0]["fiyatlar"])

    def test_normalize_scraped_data_accepts_official_regional_data(self):
        data, skipped = db_utils.normalize_scraped_data([
            {
                "marka": "Opet",
                "il": "Istanbul",
                "fiyatlar": {"Benzin": "63,50"},
                "veri_kaynagi": "api.opet.com.tr/api/fuelprices/allprices",
            },
        ])

        self.assertEqual(skipped, 0)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["isim"], "")
        self.assertEqual(data[0]["veri_kapsami"], "regional_official")

    def test_normalize_scraped_data_keeps_istanbul_region(self):
        data, skipped = db_utils.normalize_scraped_data([
            {
                "marka": "Opet",
                "il": "İSTANBUL ANADOLU",
                "fiyatlar": {"Benzin": "64,32"},
                "veri_kaynagi": "api.opet.com.tr/api/fuelprices/allprices",
            },
            {
                "marka": "Petrol Ofisi",
                "il": "ISTANBUL (AVRUPA)",
                "fiyatlar": {"Motorin": "71,77"},
                "veri_kaynagi": "petrolofisi.com.tr/akaryakit-fiyatlari",
            },
        ])

        self.assertEqual(skipped, 0)
        self.assertEqual(data[0]["il"], "ISTANBUL")
        self.assertEqual(data[0]["ilce"], "ANADOLU")
        self.assertEqual(data[1]["il"], "ISTANBUL")
        self.assertEqual(data[1]["ilce"], "AVRUPA")
        self.assertTrue(db_utils._station_district_in_istanbul_region("Kadıköy", "ANADOLU"))
        self.assertTrue(db_utils._station_district_in_istanbul_region("Beşiktaş", "AVRUPA"))

    def test_normalize_scraped_data_accepts_total_and_tp_official_sources(self):
        data, skipped = db_utils.normalize_scraped_data([
            {
                "marka": "TotalEnergies",
                "il": "İÇEL",
                "ilce": "Silifke",
                "fiyatlar": {"Benzin": "64,20"},
                "veri_kaynagi": "apimobile.guzelenerji.com.tr/exapi/fuel_prices",
            },
            {
                "marka": "TP",
                "il": "K.MARAS",
                "ilce": "Merkez",
                "fiyatlar": {"Motorin": "73,10"},
                "veri_kaynagi": "www.tppd.com.tr/akaryakit-fiyatlari",
            },
        ])

        self.assertEqual(skipped, 0)
        self.assertEqual(data[0]["marka"], "TotalEnergies")
        self.assertEqual(data[0]["il"], "MERSIN")
        self.assertEqual(data[1]["marka"], "Türkiye Petrolleri")
        self.assertEqual(data[1]["il"], "KAHRAMANMARAS")

    def test_normalize_scraped_data_rejects_generated_station_names(self):
        data, skipped = db_utils.normalize_scraped_data([
            {
                "marka": "Shell",
                "istasyon_adi": "Shell Kadikoy (Fullet Verisi)",
                "il": "Istanbul",
                "enlem": "41.01",
                "boylam": "29.01",
                "fiyatlar": {"Benzin": "63,50"},
            },
        ])

        self.assertEqual(skipped, 1)
        self.assertEqual(data, [])

    def test_station_inventory_accepts_official_rows_without_prices(self):
        data, skipped = db_utils.normalize_station_inventory_data([
            {
                "marka": "Total",
                "istasyon_adi": "Total Test Istasyonu",
                "il": "Gaziantep",
                "ilce": "Sehitkamil",
                "enlem": "37.1423",
                "boylam": "37.39111",
                "veri_kaynagi": "apimobile.guzelenerji.com.tr/exapi/stations",
            },
            {
                "marka": "Shell",
                "istasyon_adi": "Shell Test",
                "il": "Istanbul",
                "enlem": "41.01",
                "boylam": "",
                "veri_kaynagi": "find.shell.com/tr/fuel",
            },
        ])

        self.assertEqual(skipped, 1)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["marka"], "TotalEnergies")
        self.assertEqual(data[0]["il"], "GAZIANTEP")
        self.assertEqual(data[0]["ilce"], "SEHITKAMIL")

    def test_station_inventory_live_write_requires_explicit_allow_flag(self):
        old_dry = os.environ.get("FULLET_DRY_RUN")
        old_allow = os.environ.get("FULLET_ALLOW_DB_WRITE")
        os.environ["FULLET_DRY_RUN"] = "0"
        os.environ["FULLET_ALLOW_DB_WRITE"] = "0"
        try:
            summary = db_utils.save_station_inventory_to_supabase(
                [{
                    "marka": "Total",
                    "istasyon_adi": "Total Test Istasyonu",
                    "il": "Gaziantep",
                    "ilce": "Sehitkamil",
                    "enlem": "37.1423",
                    "boylam": "37.39111",
                    "veri_kaynagi": "apimobile.guzelenerji.com.tr/exapi/stations",
                }],
                default_brand="TotalEnergies",
            )
            self.assertEqual(summary.stations_touched, 0)
            self.assertEqual(summary.prices_touched, 0)
            self.assertEqual(summary.skipped_items, 1)
        finally:
            if old_dry is None:
                os.environ.pop("FULLET_DRY_RUN", None)
            else:
                os.environ["FULLET_DRY_RUN"] = old_dry
            if old_allow is None:
                os.environ.pop("FULLET_ALLOW_DB_WRITE", None)
            else:
                os.environ["FULLET_ALLOW_DB_WRITE"] = old_allow

    def test_live_write_requires_explicit_allow_flag(self):
        old_dry = os.environ.get("FULLET_DRY_RUN")
        old_allow = os.environ.get("FULLET_ALLOW_DB_WRITE")
        os.environ["FULLET_DRY_RUN"] = "0"
        os.environ["FULLET_ALLOW_DB_WRITE"] = "0"
        try:
            summary = db_utils.save_to_supabase(
                [{
                    "marka": "Opet",
                    "istasyon_adi": "Opet Test Istasyonu",
                    "il": "Istanbul",
                    "enlem": "41.01",
                    "boylam": "29.01",
                    "fiyatlar": {"Benzin": "63,50"},
                }],
                default_brand="Opet",
            )
            self.assertEqual(summary.stations_touched, 0)
            self.assertEqual(summary.prices_touched, 0)
            self.assertEqual(summary.skipped_items, 1)
        finally:
            if old_dry is None:
                os.environ.pop("FULLET_DRY_RUN", None)
            else:
                os.environ["FULLET_DRY_RUN"] = old_dry
            if old_allow is None:
                os.environ.pop("FULLET_ALLOW_DB_WRITE", None)
            else:
                os.environ["FULLET_ALLOW_DB_WRITE"] = old_allow


if __name__ == "__main__":
    unittest.main()
