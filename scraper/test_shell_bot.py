import unittest
import unittest.mock

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


class ShellTargetCoverageTest(unittest.TestCase):
    """Hedef kaybı sayılmalı ve geçici hatalarda tekrar denenmeli.

    Canlı ölçüm (8 koşu, bot_runs stdout'u): denenen ~44 hedefin ~28'i
    "Element is not visible" ile kayboluyor, ama bot yine de yüzlerce kayıt
    döndürdüğü için 'success' görünüyordu. Sabit `wait_for_timeout(750)` +
    `click(force=True)` bunun sebebiydi: `force` görünürlük kontrolünü
    ATLAMAZ, callback sürerken combobox görünmez olur.
    """

    def _run(self, outcomes):
        """`outcomes`: hedef başına sonuç listesi (deneme sırasına göre)."""
        import shell_bot

        calls = []

        def fake_scrape_target(page, city, district, column_map):
            calls.append((city, district))
            result = outcomes[(city, district)].pop(0)
            if isinstance(result, Exception):
                raise result
            return result, {"Motorin": [5]}

        targets = [{"il": c, "ilce": d} for c, d in outcomes]
        with unittest.mock.patch.object(shell_bot, "_scrape_target", fake_scrape_target), \
                unittest.mock.patch.object(shell_bot, "sync_playwright", _FakePlaywright), \
                unittest.mock.patch.object(shell_bot, "_limited_targets", lambda t: t), \
                unittest.mock.patch.object(shell_bot, "_settle", lambda page: None):
            data, stats = shell_bot.scrape_shell_data(targets)
        return data, stats, calls

    def test_transient_error_is_retried_and_counted_ok(self):
        rows = [{"marka": "Shell"}]
        _, stats, calls = self._run({
            ("ANKARA", "CANKAYA"): [Exception("Element is not visible"), rows],
        })
        self.assertEqual(
            stats,
            {"planned": 1, "attempted": 1, "ok": 1, "missing": 0, "failed": 0,
             "budget_exhausted": False},
        )
        self.assertEqual(len(calls), 2)

    def test_persistent_error_counts_as_failed(self):
        _, stats, calls = self._run({
            ("ANKARA", "CANKAYA"): [
                Exception("Element is not visible"),
                Exception("Element is not visible"),
            ],
        })
        self.assertEqual(stats["failed"], 1)
        self.assertEqual(stats["ok"], 0)
        # İki denemeden fazlası yapılmamalı (9 dakikalık kazıma bütçesi).
        self.assertEqual(len(calls), 2)

    def test_missing_option_is_not_retried(self):
        # İlçe Shell'in listesinde yoksa tekrar denemek bütçe israfıdır;
        # bu bir envanter/veri uyuşmazlığıdır, geçici hata değil.
        from shell_bot import _OptionMissing

        _, stats, calls = self._run({
            ("ISTANBUL", "HOROZLUHAN MAH Y"): [_OptionMissing("yok")],
        })
        self.assertEqual(stats["missing"], 1)
        self.assertEqual(stats["failed"], 0)
        self.assertEqual(len(calls), 1)

    def test_stats_cover_every_attempted_target(self):
        rows = [{"marka": "Shell"}]
        data, stats, _ = self._run({
            ("ANKARA", "CANKAYA"): [rows],
            ("ANKARA", "MAMAK"): [Exception("boom"), Exception("boom")],
            ("IZMIR", "KONAK"): [rows],
        })
        self.assertEqual(stats["attempted"], 3)
        self.assertEqual(stats["planned"], 3)
        self.assertEqual(stats["ok"] + stats["missing"] + stats["failed"], 3)
        self.assertEqual(len(data), 2)
        self.assertFalse(stats["budget_exhausted"])

    def test_option_lookup_uses_the_short_timeout(self):
        """Yokluk kararı 3 sn'de verilmeli, 15 sn'de değil.

        Regresyon: ilk düzeltmede tek bir 15 sn'lik timeout kullanılmıştı.
        Shell'in listesinde gerçekten bulunmayan ilçeler (envanterde mahalle
        adı yazılmış kayıtlar) eski kodda anında eleniyordu; 15 sn'lik bekleme
        150 hedeflik koşuyu 9 dk'dan ~25 dk'ya çıkarıp 1800 sn'lik subprocess
        bütçesini deldi ve bot canlıda timeout'a gitti.
        """
        import shell_bot

        self.assertLessEqual(shell_bot.OPTION_TIMEOUT_MS, 5000)
        self.assertGreater(shell_bot.ELEMENT_TIMEOUT_MS, shell_bot.OPTION_TIMEOUT_MS)

    def test_budget_stops_the_run_and_lowers_coverage(self):
        """Bütçe kesintisi kapsamayı DÜŞÜRMELİ, gizlememeli.

        Kapsama `ok/planned` üzerinden hesaplanır. `ok/attempted` kullanılsaydı
        bütçe 1 hedefte kesildiğinde "%100 kapsama" gibi sahte bir rakam
        çıkardı — oysa Shell'in geri kalanı hiç tazelenmemiş olurdu.
        """
        import shell_bot

        rows = [{"marka": "Shell"}]
        outcomes = {
            ("ANKARA", "CANKAYA"): [rows],
            ("ANKARA", "MAMAK"): [rows],
            ("IZMIR", "KONAK"): [rows],
        }
        with unittest.mock.patch.object(shell_bot, "RUN_BUDGET_SECONDS", 0):
            _, stats, calls = self._run(outcomes)

        self.assertTrue(stats["budget_exhausted"])
        self.assertEqual(stats["attempted"], 0)
        self.assertEqual(stats["planned"], 3)
        self.assertEqual(calls, [])
        # planned'a göre kapsama sıfır -> degraded. attempted'a göre olsaydı
        # 0/0 çıkar ve sorun görünmezdi.
        self.assertEqual(stats["ok"] / stats["planned"], 0.0)


class ComboSelectionTest(unittest.TestCase):
    """Açılır liste seçiminin iki ayrı semantiği karıştırılmamalı.

    Bu oturumun en pahalı hatası buydu: `.count() > 0` (VARLIK) kontrolü
    `wait_for(state="visible")` (GÖRÜNÜRLÜK) ile değiştirildi. DevExpress
    listesi kaydırılabilir ve kapalıyken de DOM'da durur; sonuç:
      * gerçek ilçeler "listede yok" sayıldı  -> yerel ölçümde kapsama %0
      * her hedef 15 sn bekledi               -> üretimde 1800 sn timeout
    Doğru ayrım: KONTEYNER görünür olmalı (liste açıldı mı?), ÖĞE ise
    yalnızca DOM'da bulunmalı (kaydırma dışında olabilir).
    """

    def _combo(self, *, listbox_visible=True, option_count=1):
        events = []

        class FakeLocator:
            def __init__(self, kind):
                self.kind = kind
                self.first = self

            def wait_for(self, state=None, timeout=None):
                events.append((self.kind, "wait_for", state))
                if self.kind == "listbox" and not listbox_visible:
                    raise RuntimeError("listbox açılmadı")

            def click(self, force=False):
                events.append((self.kind, "click", None))

            def count(self):
                events.append((self.kind, "count", None))
                return option_count

            def scroll_into_view_if_needed(self, timeout=None):
                events.append((self.kind, "scroll", None))

            def evaluate(self, script):
                events.append((self.kind, "evaluate", None))

        class FakeKeyboard:
            def press(self, key):
                events.append(("keyboard", "press", key))

        class FakePage:
            keyboard = FakeKeyboard()

            def locator(self, selector):
                if "B-1Img" in selector:
                    return FakeLocator("button")
                if "td:has-text" in selector:
                    return FakeLocator("option")
                return FakeLocator("listbox")

            def wait_for_timeout(self, ms):
                events.append(("page", "sleep", ms))

            def wait_for_selector(self, selector, state=None, timeout=None):
                events.append(("page", "wait_selector", state))

        return FakePage(), events

    def test_option_presence_is_checked_with_count_not_visibility(self):
        import shell_bot

        page, events = self._combo()
        shell_bot._select_from_combo(
            page, "#cb_all_cb_county_B-1Img", "#cb_all_cb_county_DDD_L_LBT", "CANKAYA"
        )
        option_events = [e for e in events if e[0] == "option"]
        self.assertIn(("option", "count", None), option_events)
        # Öğe için GÖRÜNÜRLÜK beklenmemeli — kaydırma dışındaki gerçek
        # ilçeleri "yok" sayan hata tam olarak buydu.
        self.assertNotIn("wait_for", [e[1] for e in option_events])

    def test_listbox_visibility_is_required(self):
        """Konteyner görünür olmalı: liste kapalıyken de DOM'da durduğu için
        tek ayırt edici sinyal budur."""
        import shell_bot

        page, events = self._combo()
        shell_bot._select_from_combo(
            page, "#cb_all_cb_county_B-1Img", "#cb_all_cb_county_DDD_L_LBT", "CANKAYA"
        )
        self.assertIn(("listbox", "wait_for", "visible"), events)

    def test_unopenable_dropdown_is_an_error_not_a_missing_option(self):
        # Liste hiç açılamadıysa "ilçe yok" demek yanlış teşhistir; bu
        # geçici bir etkileşim hatasıdır ve retry hakkı olmalıdır.
        import shell_bot

        page, _ = self._combo(listbox_visible=False)
        with self.assertRaises(RuntimeError):
            shell_bot._select_from_combo(
                page, "#cb_all_cb_county_B-1Img", "#cb_all_cb_county_DDD_L_LBT", "X"
            )

    def test_absent_option_raises_option_missing(self):
        import shell_bot

        page, _ = self._combo(option_count=0)
        with self.assertRaises(shell_bot._OptionMissing):
            shell_bot._select_from_combo(
                page, "#cb_all_cb_county_B-1Img", "#cb_all_cb_county_DDD_L_LBT",
                "HOROZLUHAN MAH Y",
            )


class _FakePage:
    def goto(self, *args, **kwargs):
        return None


class _FakeBrowser:
    def new_page(self):
        return _FakePage()

    def close(self):
        return None


class _FakePlaywright:
    """`with sync_playwright() as p:` protokolünü taklit eder."""

    def __init__(self):
        self.chromium = self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def launch(self, **kwargs):
        return _FakeBrowser()


if __name__ == "__main__":
    unittest.main()
