import os
import unittest
from unittest import mock

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


    def test_fuzzy_match_rural_station_sivas_kangal(self):
        from matching import _fuzzy_match_name
        self.assertTrue(_fuzzy_match_name("Kangal Petrol", "Kangal Akaryakit"))
        self.assertTrue(_fuzzy_match_name("Kangal A.Ş.", "Kangal"))
        self.assertTrue(_fuzzy_match_name("Ahmet Akaryakıt", "Ahmet Petrol"))

    def test_fuzzy_match_low_confidence_should_fail(self):
        from matching import _fuzzy_match_name
        self.assertFalse(_fuzzy_match_name("Ahmet Petrol", "Mehmet Petrol"))
        self.assertFalse(_fuzzy_match_name("Sivas Akaryakıt", "Kangal Akaryakıt"))

    def test_haversine_distance(self):
        from matching import _haversine
        # ~111 km per degree of latitude
        dist = _haversine(41.0, 29.0, 42.0, 29.0)
        self.assertTrue(110 < dist < 112)

    @unittest.mock.patch('database_writes.supabase')
    def test_zero_cost_unchanged_prices_skipped(self, mock_supabase):
        from database_writes import _bulk_upsert_prices
        from datetime import datetime, timezone
        
        # Mock the existing prices DB response
        mock_response = unittest.mock.MagicMock()
        mock_response.data = [{
            "istasyon_id": "st_1",
            "yakit_tipi": "Motorin",
            "fiyat": 40.0,
            "price_status": "fresh",
            "son_guncelleme": datetime.now(timezone.utc).isoformat()
        }]
        
        # Setup the mock chain: supabase.table().select().in_().execute() -> mock_response
        mock_table = unittest.mock.MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.in_.return_value.execute.return_value = mock_response

        # Test zero-cost unchanged
        touched = _bulk_upsert_prices([{"istasyon_id": "st_1", "yakit_tipi": "Motorin", "fiyat": 40.0}])
        self.assertEqual(touched, 0)
        mock_table.upsert.assert_not_called()
        
        # Test changed price -> should upsert
        touched_changed = _bulk_upsert_prices([{"istasyon_id": "st_1", "yakit_tipi": "Motorin", "fiyat": 41.0}])
        self.assertEqual(touched_changed, 1)
        mock_table.upsert.assert_called_once()

    @unittest.mock.patch('database_writes.supabase')
    def test_deleted_fuel_becomes_unknown(self, mock_supabase):
        from database_writes import _mark_unreported_prices_unknown
        
        mock_table = unittest.mock.MagicMock()
        mock_supabase.table.return_value = mock_table
        
        # We report Motorin, so Kursunsuz 95, LPG, Elektrik should be marked unknown
        _mark_unreported_prices_unknown(["st_1"], {"Motorin"})
        
        # Since CANONICAL_FUELS has 4 items, 3 should be "deleted" (updated to unknown)
        self.assertEqual(mock_table.update.call_count, 3)
        mock_table.update.assert_any_call({"price_status": "unknown"})

    @unittest.mock.patch('matching.supabase')
    @unittest.mock.patch('database_writes.supabase')
    def test_official_station_without_price_is_low_priority(self, mock_dbw, mock_match):
        from database_writes import _bulk_write_station_inventory
        
        # Mock empty existing db
        mock_table = unittest.mock.MagicMock()
        mock_dbw.table.return_value = mock_table
        mock_match.table.return_value.select.return_value.eq.return_value.range.return_value.execute.return_value.data = []

        _bulk_write_station_inventory([{
            "marka": "Opet",
            "isim": "Test",
            "il": "ISTANBUL",
            "ilce": "KADIKOY",
            "enlem": 41.0,
            "boylam": 29.0,
            "veri_kaynagi": "test"
        }])
        
        # It should insert a new row with visibility_status = low_priority and aktif = True
        mock_table.insert.assert_called_once()
        inserted_row = mock_table.insert.call_args[0][0][0]
        self.assertEqual(inserted_row["visibility_status"], "low_priority")
        self.assertTrue(inserted_row["aktif"])


class ProvinceSplitTest(unittest.TestCase):
    """`il` kolonu "İLÇE/İL" birleşik yazılmış 20 istasyon vardı ve
    `_station_targets` `.eq("il", "KONYA")` sorguladığı için hiçbiri
    eşleşmiyordu — canlı ölçümde 20'sinin de 0 taze fiyatı vardı."""

    def test_district_slash_province_is_resolved(self):
        from normalization import split_province_district

        self.assertEqual(split_province_district("MERAM/KONYA"), ("KONYA", "MERAM"))
        self.assertEqual(
            split_province_district("KECIOREN/ANKARA"), ("ANKARA", "KECIOREN")
        )

    def test_either_order_is_accepted(self):
        # Kaynaklar iki sırayı da kullanıyor; karar konuma değil 81 il
        # listesine göre verilir.
        from normalization import split_province_district

        self.assertEqual(split_province_district("MUGLA/MARMARIS"), ("MUGLA", "MARMARIS"))

    def test_spaces_around_slash_are_tolerated(self):
        from normalization import split_province_district

        self.assertEqual(split_province_district("MERAM / KONYA"), ("KONYA", "MERAM"))

    def test_plain_province_is_untouched(self):
        from normalization import normalize_province, split_province_district

        self.assertEqual(split_province_district("KONYA"), ("", ""))
        self.assertEqual(normalize_province("KONYA"), "KONYA")
        self.assertEqual(normalize_province("İstanbul"), "ISTANBUL")

    def test_ambiguous_pair_is_left_alone(self):
        # İki taraf da il ise hangisinin il olduğu bilinemez; uydurma yapma.
        from normalization import split_province_district

        self.assertEqual(split_province_district("KONYA/ANKARA"), ("", ""))

    def test_scraped_item_recovers_province_and_district(self):
        item = db_utils.normalize_scraped_item(
            {"marka": "Opet", "il": "MERAM/KONYA", "fiyatlar": {"Motorin": 82.1},
             "veri_kaynagi": "api.opet.com.tr/api/fuelprices/allprices"},
            default_brand="Opet",
        )
        self.assertIsNotNone(item)
        self.assertEqual(item["il"], "KONYA")
        self.assertEqual(item["ilce"], "MERAM")

    def test_explicit_district_wins_over_embedded_one(self):
        item = db_utils.normalize_scraped_item(
            {"marka": "Opet", "il": "MERAM/KONYA", "ilce": "SELCUKLU",
             "fiyatlar": {"Motorin": 82.1},
             "veri_kaynagi": "api.opet.com.tr/api/fuelprices/allprices"},
            default_brand="Opet",
        )
        self.assertEqual(item["il"], "KONYA")
        self.assertEqual(item["ilce"], "SELCUKLU")


class StationProximityIndexTest(unittest.TestCase):
    """Faz 3 / F3-1: istasyon kimligi KOVA degil YAKINLIK olmali.

    Eski anahtar (marka, il, ilce, round(lat,4), round(lon,4)) 11 m'lik bir
    kovaydi. Canli olcum: 100 aktif kopya cifti, mesafeler 0-12 m, 98'inde
    ikisinde de fiyat vardi, 6'si ayni yakitta FARKLI fiyat gosteriyordu.
    """

    # Canli kopya ciftlerinden olculen gercek mesafeler (metre)
    ISTANBUL_CEKMEKOY = (41.0396, 29.1795)

    def _offset(self, point, meters_north):
        # 1 derece enlem ~ 111.320 m
        return (point[0] + meters_north / 111320.0, point[1])

    def test_near_duplicate_matches_same_station(self):
        from matching import StationProximityIndex

        index = StationProximityIndex()
        index.add("Shell", *self.ISTANBUL_CEKMEKOY, "station-1")
        # Canlida 8 m arayla iki kayit vardi ('Shell' + 'CEKMEKOY AKCESME.')
        near = self._offset(self.ISTANBUL_CEKMEKOY, 8)
        self.assertEqual(index.find("Shell", *near), "station-1")

    def test_twelve_meters_still_matches(self):
        # Eski round(...,4) kovasinin KIRILDIGI mesafe: 12 m ayri iki nokta
        # farkli kovalara dusup 'ayri istasyon' sayilabiliyordu.
        from matching import StationProximityIndex

        index = StationProximityIndex()
        index.add("Shell", *self.ISTANBUL_CEKMEKOY, "station-1")
        self.assertEqual(
            index.find("Shell", *self._offset(self.ISTANBUL_CEKMEKOY, 12)),
            "station-1",
        )

    def test_cell_boundary_does_not_hide_neighbour(self):
        # Kova-esitliginin asil kirildigi yer: sinirin iki yaninda duran cift.
        from matching import StationProximityIndex

        index = StationProximityIndex()
        on_boundary = (41.00999, 29.1795)  # 0.01'lik hucre sinirinin hemen altinda
        index.add("Shell", *on_boundary, "station-1")
        just_over = (41.01001, 29.1795)    # ~2 m kuzeyi, DIGER hucre
        self.assertEqual(index.find("Shell", *just_over), "station-1")

    def test_genuinely_separate_stations_stay_separate(self):
        # Regresyon korumasi: yaricap disi ayri istasyonlar birlestirilmemeli.
        # D4 notu: 2,4 km ve 3,5 km uzaktaki kayitlar KOPYA DEGIL.
        from matching import StationProximityIndex

        index = StationProximityIndex()
        index.add("Petrol Ofisi", *self.ISTANBUL_CEKMEKOY, "station-1")
        far = self._offset(self.ISTANBUL_CEKMEKOY, 2400)
        self.assertIsNone(index.find("Petrol Ofisi", *far))

    def test_different_brands_never_match(self):
        from matching import StationProximityIndex

        index = StationProximityIndex()
        index.add("Shell", *self.ISTANBUL_CEKMEKOY, "shell-1")
        near = self._offset(self.ISTANBUL_CEKMEKOY, 5)
        self.assertIsNone(index.find("Opet", *near))

    def test_identity_ignores_administrative_fields(self):
        # ilce='' vs ilce='CEKMEKOY' tek basina kopya uretiyordu; kimlik artik
        # yalnizca marka + konum.
        from matching import StationProximityIndex, station_coordinates

        index = StationProximityIndex()
        row = {"marka": "Shell", "enlem": self.ISTANBUL_CEKMEKOY[0],
               "boylam": self.ISTANBUL_CEKMEKOY[1], "il": "ISTANBUL", "ilce": ""}
        coordinates = station_coordinates(row)
        self.assertIsNotNone(coordinates)
        index.add(row["marka"], *coordinates, "station-1")

        same_place_with_district = {"marka": "Shell", "enlem": self.ISTANBUL_CEKMEKOY[0],
                                    "boylam": self.ISTANBUL_CEKMEKOY[1],
                                    "il": "ISTANBUL", "ilce": "CEKMEKOY"}
        other = station_coordinates(same_place_with_district)
        self.assertEqual(index.find("Shell", *other), "station-1")


if __name__ == "__main__":
    unittest.main()
