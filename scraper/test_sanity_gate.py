import unittest
import unittest.mock


def _items(fuel, price, count=10):
    return [
        {"marka": "Shell", "il": f"IL{i}", "fiyatlar": {fuel: price}}
        for i in range(count)
    ]


class SanityGateTest(unittest.TestCase):
    def _patch_reference(self, medians):
        return unittest.mock.patch(
            "sanity_gate._reference_medians", return_value=medians
        )

    def test_shell_lpg_column_error_is_rejected(self):
        """Yol haritası S1-4 regresyon kilidi.

        Gerçek olay: Shell LPG'ye kilogram başına fuel oil fiyatı (37,68)
        yazılıyordu; diğer markalar ~31,3. Sapma %20 — kapı bunu tutmalı.
        """
        from sanity_gate import check_fuel_sanity

        with self._patch_reference({"LPG": 31.30}):
            rejected, reasons = check_fuel_sanity(_items("LPG", 37.68), "Shell")

        self.assertEqual(rejected, {"LPG"})
        self.assertIn("37.68", reasons["LPG"])
        self.assertIn("31.30", reasons["LPG"])

    def test_normal_regional_spread_is_accepted(self):
        # Canlı ölçüm: markalar arası medyan fark kuruş mertebesinde.
        from sanity_gate import check_fuel_sanity

        with self._patch_reference({"LPG": 31.30}):
            rejected, _ = check_fuel_sanity(_items("LPG", 31.35), "Shell")
        self.assertEqual(rejected, set())

    def test_gate_is_per_fuel_not_per_brand(self):
        """LPG reddedilse bile Motorin yazılmaya devam etmeli."""
        from sanity_gate import apply_sanity_gate

        items = [
            {"marka": "Shell", "il": f"IL{i}",
             "fiyatlar": {"LPG": 37.68, "Motorin": 81.75}}
            for i in range(10)
        ]
        with self._patch_reference({"LPG": 31.30, "Motorin": 82.00}), \
                unittest.mock.patch("sanity_gate.create_system_alert") as alert, \
                unittest.mock.patch("sanity_gate.resolve_system_alerts"):
            filtered, rejected = apply_sanity_gate(items, "Shell")

        self.assertEqual(len(filtered), 10)
        for item in filtered:
            self.assertNotIn("LPG", item["fiyatlar"])
            self.assertEqual(item["fiyatlar"]["Motorin"], 81.75)
        # Reddedilen yakıt çağırana bildirilmeli: "raporlanmayanı unknown yap"
        # süpürgesi bu yakıtı muaf tutmazsa kapı, koruduğu veriyi siler.
        self.assertEqual(rejected, {"LPG"})
        alert.assert_called_once()
        self.assertEqual(alert.call_args.kwargs["severity"], "critical")

    def test_small_samples_are_not_gated(self):
        # Tek tük örnekte medyan anlamsız; kapı uygulanmamalı.
        from sanity_gate import check_fuel_sanity

        with self._patch_reference({"LPG": 31.30}):
            rejected, _ = check_fuel_sanity(_items("LPG", 37.68, count=2), "Shell")
        self.assertEqual(rejected, set())

    def test_missing_reference_disables_the_gate(self):
        # Karşılaştırılacak marka yoksa yazmayı engellemek daha zararlı olur.
        from sanity_gate import check_fuel_sanity

        with self._patch_reference({}):
            rejected, _ = check_fuel_sanity(_items("LPG", 37.68), "Shell")
        self.assertEqual(rejected, set())

    def test_items_left_without_any_fuel_are_dropped(self):
        from sanity_gate import apply_sanity_gate

        with self._patch_reference({"LPG": 31.30}), \
                unittest.mock.patch("sanity_gate.create_system_alert"), \
                unittest.mock.patch("sanity_gate.resolve_system_alerts"):
            filtered, rejected = apply_sanity_gate(_items("LPG", 37.68), "Shell")
        self.assertEqual(filtered, [])
        self.assertEqual(rejected, {"LPG"})

    def test_rejected_fuel_is_exempt_from_unknown_sweep(self):
        """Kapı reddettiği yakıtı unknown süpürgesinden muaf tutmalı.

        Regresyon: kapı LPG'yi reddedince LPG öğelerden düşüyor, süpürge de
        onu "bu koşuda raporlanmadı" sayıp mevcut SAĞLAM LPG fiyatlarını
        unknown'a çeviriyordu. Kapı, koruması gereken veriyi siliyordu.
        """
        import db_utils

        with self._patch_reference({"LPG": 31.30, "Motorin": 82.00}), \
                unittest.mock.patch("sanity_gate.create_system_alert"), \
                unittest.mock.patch("sanity_gate.resolve_system_alerts"):
            kept, rejected = db_utils._apply_sanity_gate_for_brands([
                {"marka": "Shell", "il": f"IL{i}",
                 "fiyatlar": {"LPG": 37.68, "Motorin": 81.75}}
                for i in range(10)
            ])

        self.assertEqual(rejected, {"LPG"})
        self.assertEqual(len(kept), 10)
        self.assertTrue(all("LPG" not in item["fiyatlar"] for item in kept))


if __name__ == "__main__":
    unittest.main()
