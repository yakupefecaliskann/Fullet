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


class KaynakButunluguTest(unittest.TestCase):
    """Aytemiz vakası (4 Ağustos 2026) regresyon kilidi.

    Aytemiz'in fiyat tablosundaki İKİ fiyat da yanlıştı ama yalnızca biri
    ana eşiği aşabildi:

        Motorin  67,17 TL  (piyasa 82,14)  -> sapma %18,9  reddedildi
        Benzin   64,86 TL  (piyasa 68,20)  -> sapma  %5,6  GEÇTİ

    Geçen benzin fiyatı 81 ilin 79'unda "en ucuz" çıkıp kullanıcıyı yanlış
    istasyona yönlendirdi. İki fiyat da aynı HTML tablosundan geliyordu.
    """

    def _patch_reference(self, medians):
        return unittest.mock.patch(
            "sanity_gate._reference_medians", return_value=medians
        )

    def _aytemiz_items(self):
        return [
            {"marka": "Aytemiz", "il": f"IL{i}",
             "fiyatlar": {"Motorin": 67.17, "Kursunsuz 95": 64.86}}
            for i in range(10)
        ]

    def test_kardes_yakit_da_sapiyorsa_reddedilir(self):
        from sanity_gate import check_fuel_sanity

        with self._patch_reference({"Motorin": 82.14, "Kursunsuz 95": 68.20}):
            rejected, reasons = check_fuel_sanity(self._aytemiz_items(), "Aytemiz")

        self.assertEqual(rejected, {"Motorin", "Kursunsuz 95"})
        self.assertIn("kaynağın bütünlüğü", reasons["Kursunsuz 95"])

    def test_temiz_kardes_yakit_korunur(self):
        """Shell LPG vakası bozulmamalı: Motorin %0,3 sapiyordu, tertemizdi.

        Kaynak butunlugu kurali fazla genis olursa saglam veriyi de atar —
        bu test o asiriligi engeller.
        """
        from sanity_gate import check_fuel_sanity

        items = [
            {"marka": "Shell", "il": f"IL{i}",
             "fiyatlar": {"LPG": 37.68, "Motorin": 81.75}}
            for i in range(10)
        ]
        with self._patch_reference({"LPG": 31.30, "Motorin": 82.00}):
            rejected, _ = check_fuel_sanity(items, "Shell")

        self.assertEqual(rejected, {"LPG"})

    def test_hicbir_yakit_reddedilmezse_kural_devreye_girmez(self):
        from sanity_gate import check_fuel_sanity

        items = [
            {"marka": "Opet", "il": f"IL{i}",
             "fiyatlar": {"Motorin": 82.50, "Kursunsuz 95": 65.00}}
            for i in range(10)
        ]
        # Kursunsuz 95 tek basina %4,7 sapiyor ama hicbir kardes reddedilmedi.
        with self._patch_reference({"Motorin": 82.60, "Kursunsuz 95": 68.20}):
            rejected, _ = check_fuel_sanity(items, "Opet")

        self.assertEqual(rejected, set())


if __name__ == "__main__":
    unittest.main()
