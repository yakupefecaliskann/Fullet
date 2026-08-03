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

        def fake_scrape_target(page, city, district, column_map, state):
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


class _FakeCombo:
    """DevExpress combobox'ının Playwright'sız taklidi.

    `selects_after` tıklamanın KAÇINCI denemede tuttuğunu belirler: canlı
    davranışın çekirdeği budur — tıklama hiçbir istisna fırlatmadan sessizce
    boşa gidebilir.
    """

    def __init__(self, items, selects_after=0, popup_opens=True):
        self.items = list(items)
        self.selects_after = selects_after
        self.popup_opens = popup_opens
        self.text = "Seçiniz"
        self.clicks = 0
        self.opened = 0


class _FakeComboPage:
    def __init__(self, combos):
        self.combos = combos
        self.events = []

    # --- Playwright yüzeyi
    def locator(self, selector):
        return _FakeComboLocator(self, selector)

    def wait_for_timeout(self, ms):
        self.events.append(("sleep", ms))

    def evaluate(self, script, arg=None):
        if "GetText" in script:
            return self.combos[arg].text
        if "GetItemCount" in script:
            return list(self.combos[arg].items)
        if "HideDropDown" in script:
            self.events.append(("hide", arg))
            return None
        return None


class _FakeComboLocator:
    def __init__(self, page, selector, index=None):
        self.page = page
        self.selector = selector
        self.index = index

    @property
    def _combo(self):
        return self.page.combos["cb_province" if "province" in self.selector else "cb_county"]

    def wait_for(self, state=None, timeout=None):
        if state == "visible" and self.selector.endswith("_LBT"):
            if not self._combo.popup_opens:
                raise RuntimeError("liste açılmadı")

    def click(self, force=False, timeout=None):
        combo = self._combo
        if "B-1Img" in self.selector:      # düğme: listeyi açar
            combo.opened += 1
            return
        combo.clicks += 1
        # Seçim ancak yeterince deneme yapıldıktan sonra "tutar".
        if combo.clicks > combo.selects_after:
            combo.text = combo.items[self.index]

    def all_inner_texts(self):
        return list(self._combo.items)

    def nth(self, index):
        return _FakeComboLocator(self.page, self.selector, index)

    def scroll_into_view_if_needed(self, timeout=None):
        pass

    def bounding_box(self):
        return {"x": 0, "y": 0, "width": 200, "height": 300}


class VerifiedSelectionTest(unittest.TestCase):
    """Seçim DOĞRULANMADAN devam edilmemeli.

    Bu botun en pahalı hatası "tıkladım, olmuştur" varsayımıydı. Canlı ölçüm
    (3 Ağu 2026): ANKARA'dan sonraki il seçimleri sessizce boşa gidiyordu —
    istisna yok, ağ isteği yok, `cb_province.GetText()` hâlâ önceki il.
    `click(force=True)` Playwright'ın "stable" kontrolünü atladığı için
    tıklama, DevExpress popup'ının bir an sonra terk ettiği koordinata
    gidiyordu. Görünen belirti "ilçe listesi bir il geriden geliyor"du; oysa
    liste DOĞRUYDU, seçilen il yanlıştı.
    """

    def _page(self, **kwargs):
        return _FakeComboPage({
            "cb_province": _FakeCombo(["ANKARA", "İSTANBUL", "İZMİR"], **kwargs),
            "cb_county": _FakeCombo(["ÇANKAYA", "KEÇİÖREN"]),
        })

    def test_silently_failed_click_is_retried_until_verified(self):
        """Asıl regresyon kilidi: ilk tıklama boşa giderse tekrar denenmeli."""
        import shell_bot

        page = self._page(selects_after=1)
        shell_bot._select_verified(
            page, "cb_province", "#cb_all_cb_province_B-1Img",
            "#cb_all_cb_province_DDD_L_LBT", "ISTANBUL",
        )
        self.assertEqual(page.combos["cb_province"].text, "İSTANBUL")
        self.assertEqual(page.combos["cb_province"].clicks, 2)

    def test_never_returns_while_combobox_still_holds_the_old_value(self):
        # Tıklama hiç tutmuyorsa sessizce başarılı dönmek YASAK: bu, bir ilin
        # bütün hedeflerinin yanlış listede aranmasına yol açıyordu.
        import shell_bot

        page = self._page(selects_after=99)
        with self.assertRaises(RuntimeError):
            shell_bot._select_verified(
                page, "cb_province", "#cb_all_cb_province_B-1Img",
                "#cb_all_cb_province_DDD_L_LBT", "ISTANBUL",
            )
        self.assertEqual(page.combos["cb_province"].text, "Seçiniz")

    def test_already_selected_value_is_not_reclicked(self):
        import shell_bot

        page = self._page()
        page.combos["cb_province"].text = "İSTANBUL"
        shell_bot._select_verified(
            page, "cb_province", "#cb_all_cb_province_B-1Img",
            "#cb_all_cb_province_DDD_L_LBT", "ISTANBUL",
        )
        self.assertEqual(page.combos["cb_province"].clicks, 0)

    def test_option_is_matched_on_normalized_text_not_raw(self):
        """Shell listesi Türkçe yazıyor, hedeflerimiz ASCII.

        `td:has-text('CANKAYA')` büyük/küçük harfe duyarsız ama AKSANA
        duyarlıdır; 'ÇANKAYA' ile eşleşmez. İki tarafı da normalize etmek şart.
        """
        import shell_bot

        page = self._page()
        shell_bot._select_verified(
            page, "cb_county", "#cb_all_cb_county_B-1Img",
            "#cb_all_cb_county_DDD_L_LBT", "KECIOREN",
        )
        self.assertEqual(page.combos["cb_county"].text, "KEÇİÖREN")

    def test_absent_option_raises_option_missing(self):
        import shell_bot

        page = self._page()
        with self.assertRaises(shell_bot._OptionMissing):
            shell_bot._select_verified(
                page, "cb_county", "#cb_all_cb_county_B-1Img",
                "#cb_all_cb_county_DDD_L_LBT", "HOROZLUHAN MAH Y",
            )

    def test_exact_match_prevents_substring_false_targets(self):
        # Alt dize eşleşmesi 'YENI' hedefini 'YENIMAHALLE'ye bağlardı.
        import shell_bot

        page = _FakeComboPage({"cb_county": _FakeCombo(["YENİMAHALLE", "YENİKENT"])})
        with self.assertRaises(shell_bot._OptionMissing):
            shell_bot._select_verified(
                page, "cb_county", "#cb_all_cb_county_B-1Img",
                "#cb_all_cb_county_DDD_L_LBT", "YENI",
            )

    def test_unopenable_dropdown_is_an_error_not_a_missing_option(self):
        # Liste hiç açılamadıysa "ilçe yok" demek yanlış teşhistir; bu geçici
        # bir etkileşim hatasıdır ve retry hakkı olmalıdır.
        import shell_bot

        page = self._page(popup_opens=False)
        with self.assertRaises(RuntimeError):
            shell_bot._select_verified(
                page, "cb_province", "#cb_all_cb_province_B-1Img",
                "#cb_all_cb_province_DDD_L_LBT", "ISTANBUL",
            )


class CountyCascadeTest(unittest.TestCase):
    """İl değişince ilçe listesinin YENİLENMESİ beklenmeli.

    Cascade, History.aspx'e giden bir POST callback'i; canlı ölçümde
    0,11–0,35 sn sürüyor. Beklemezsek liste bir an ÖNCEKİ ilin ilçelerini
    gösterir ve o aralıkta okursak yanlış listede ararız.
    """

    def _page(self, snapshots):
        state = {"i": 0}

        class FakePage:
            def evaluate(self, script, arg=None):
                index = min(state["i"], len(snapshots) - 1)
                state["i"] += 1
                return list(snapshots[index])

            def wait_for_timeout(self, ms):
                pass

        return FakePage()

    def test_waits_until_the_county_list_changes(self):
        import shell_bot

        page = self._page([["ADALAR", "SILE"], ["ADALAR", "SILE"], ["CANKAYA", "MAMAK"]])
        self.assertTrue(shell_bot._wait_county_cascade(page, ["ADALAR", "SILE"]))

    def test_gives_up_without_blocking_forever(self):
        import shell_bot

        page = self._page([["ADALAR", "SILE"]])
        with unittest.mock.patch.object(shell_bot, "COUNTY_CASCADE_TIMEOUT_MS", 200):
            self.assertFalse(shell_bot._wait_county_cascade(page, ["ADALAR", "SILE"]))


class TargetPaginationTest(unittest.TestCase):
    """Hedef listesi 1000 satırda SESSİZCE kesilmemeli.

    PostgREST tek istekte en fazla 1000 satır döndürür. Shell'in 1414
    istasyonu var; sayfalamasız sorgu 414'ünü hiç görmüyordu. Sonuç iki
    katmanlı: (1) o il/ilçeler hiç tazelenmiyordu — 152 istasyon 30+ gündür
    doğrulanmamıştı, (2) kapsama oranının PAYDASI eksik olduğu için ölçüm
    kendini olduğundan iyi gösteriyordu.
    """

    def _supabase(self, total):
        istasyonlar = [
            {"il": "ANKARA", "ilce": f"ILCE{i:04d}"} for i in range(total)
        ]
        calls = []

        class FakeQuery:
            def select(self, *a, **k):
                return self

            def eq(self, *a, **k):
                return self

            @property
            def not_(self):
                return self

            def is_(self, *a, **k):
                return self

            def range(self, start, end):
                calls.append((start, end))
                self._slice = istasyonlar[start:end + 1]
                return self

            def execute(self):
                return unittest.mock.Mock(data=list(self._slice))

        class FakeSupabase:
            def table(self, name):
                return FakeQuery()

        return FakeSupabase(), calls

    def test_every_station_is_read_not_just_the_first_page(self):
        import shell_bot

        supabase, calls = self._supabase(1414)
        with unittest.mock.patch.object(shell_bot, "supabase", supabase):
            targets = shell_bot._targets_from_supabase()

        self.assertEqual(len(calls), 2)                  # 1000 + 414
        self.assertEqual(len(targets), 1414)

    def test_single_page_does_not_make_a_second_request(self):
        import shell_bot

        supabase, calls = self._supabase(120)
        with unittest.mock.patch.object(shell_bot, "supabase", supabase):
            targets = shell_bot._targets_from_supabase()

        self.assertEqual(len(calls), 1)
        self.assertEqual(len(targets), 120)

    def test_exactly_one_full_page_still_checks_for_more(self):
        # 1000 satır dönmesi "hepsi bu" demek DEĞİL; sınır tam da burada.
        import shell_bot

        supabase, calls = self._supabase(1000)
        with unittest.mock.patch.object(shell_bot, "supabase", supabase):
            targets = shell_bot._targets_from_supabase()

        self.assertEqual(len(calls), 2)
        self.assertEqual(len(targets), 1000)


class GridRefreshTest(unittest.TestCase):
    """Arama sonrası grid'in DOĞRU İLE ait olması beklenmeli.

    Canlı ölçüm (3 Ağu, 150 hedeflik yerel koşu): kalan 19 hatanın 18'i
    "grid X yerine başka ilin satırlarını döndürdü"ydü ve her biri bir ilin
    İLK hedefiydi. Yükleme göstergesinin kaybolması grid'in yenilendiği
    anlamına gelmiyor; tek belirleyici sinyal grid'in kendi İl kolonu.
    """

    def _page(self, cities):
        state = {"i": 0}

        class FakePage:
            def evaluate(self, script, arg=None):
                index = min(state["i"], len(cities) - 1)
                state["i"] += 1
                return cities[index]

            def wait_for_timeout(self, ms):
                pass

        return FakePage()

    def test_waits_until_the_grid_shows_the_selected_province(self):
        import shell_bot

        page = self._page(["ANKARA", "ANKARA", "İSTANBUL"])
        self.assertTrue(shell_bot._wait_for_grid(page, "ISTANBUL"))

    def test_empty_grid_does_not_end_the_wait_early(self):
        """Satırlar bir an silinip yeniden doluyor olabilir; boş grid'de
        erken dönmek sessiz bir eksik sayımdır."""
        import shell_bot

        page = self._page([None, None, "İSTANBUL"])
        self.assertTrue(shell_bot._wait_for_grid(page, "ISTANBUL"))

    def test_gives_up_when_the_grid_never_matches(self):
        import shell_bot

        page = self._page(["ANKARA"])
        with unittest.mock.patch.object(shell_bot, "GRID_MATCH_TIMEOUT_MS", 200):
            self.assertFalse(shell_bot._wait_for_grid(page, "ISTANBUL"))


class ProvinceStatePoisoningTest(unittest.TestCase):
    """Tek bir başarısız il seçimi, o ilin TAMAMINI kaybettirmemeli.

    Üretim kanıtı (3 Ağu gece koşusu, kapsama %23): ISTANBUL'un ilk hedefinde
    bir seçim kaçtı; `state["city"]` yine de "ISTANBUL" yazıldığı için sonraki
    39 hedefte il BİR DAHA HİÇ seçilmedi ve hepsi ANKARA'nın ilçe listesinde
    arandı. 40 hedefin 40'ı "listede yok" sayıldı. Cascade hatası yaşayan 6
    ilde toplam 63 hedef böyle kayboldu.
    """

    def test_failed_selection_does_not_mark_the_province_as_selected(self):
        import shell_bot

        state = {"city": "ANKARA"}
        page = unittest.mock.Mock()
        with unittest.mock.patch.object(shell_bot, "_settle", lambda *a, **k: None), \
                unittest.mock.patch.object(shell_bot, "_combo_items", lambda *a: []), \
                unittest.mock.patch.object(
                    shell_bot, "_select_verified",
                    unittest.mock.Mock(side_effect=RuntimeError("seçim doğrulanamadı"))):
            with self.assertRaises(RuntimeError):
                shell_bot._scrape_target(page, "ISTANBUL", "KADIKOY", {"Motorin": [5]}, state)

        # En kritik satır: il "seçili" işaretlenmiş OLMAMALI.
        self.assertIsNone(state["city"])

    def test_stalled_cascade_does_not_mark_the_province_as_selected(self):
        import shell_bot

        state = {"city": "ANKARA"}
        page = unittest.mock.Mock()
        with unittest.mock.patch.object(shell_bot, "_settle", lambda *a, **k: None), \
                unittest.mock.patch.object(shell_bot, "_combo_items", lambda *a: []), \
                unittest.mock.patch.object(shell_bot, "_select_verified", lambda *a: None), \
                unittest.mock.patch.object(shell_bot, "_wait_county_cascade", lambda *a: False):
            with self.assertRaises(RuntimeError):
                shell_bot._scrape_target(page, "ISTANBUL", "KADIKOY", {"Motorin": [5]}, state)

        self.assertIsNone(state["city"])

    def test_already_selected_province_does_not_wait_for_a_cascade(self):
        """İl zaten seçiliyse yeni bir cascade BEKLENMEMELİ.

        Regresyon: hedef, il seçiminden SONRAKİ bir aşamada hata alabilir —
        ilk hedefte grid henüz boş olduğu için "kolon başlıkları okunamadı"
        ile bir kez yeniden denenir. İkinci denemede combobox zaten o ili
        gösterdiği için hiçbir cascade tetiklenmez. Liste değişimini şart
        koşmak, ilk düzeltmede ANKARA'nın 16 hedefinin tamamını kaybettirdi.
        """
        import shell_bot

        state = {"city": None}          # önceki hata state'i temizlemiş
        page = unittest.mock.Mock()
        page.locator.return_value.all.return_value = []
        cascade = unittest.mock.Mock(return_value=False)

        with unittest.mock.patch.object(shell_bot, "_settle", lambda *a, **k: None), \
                unittest.mock.patch.object(shell_bot, "_combo_text", lambda *a: "ANKARA"), \
                unittest.mock.patch.object(shell_bot, "_combo_items", lambda *a: ["ÇANKAYA"]), \
                unittest.mock.patch.object(shell_bot, "_select_verified", lambda *a: None), \
                unittest.mock.patch.object(shell_bot, "_wait_for_grid", lambda *a: True), \
                unittest.mock.patch.object(shell_bot, "_wait_county_cascade", cascade):
            rows, _ = shell_bot._scrape_target(
                page, "ANKARA", "CANKAYA", {"Motorin": [5]}, state)

        self.assertEqual(rows, [])
        cascade.assert_not_called()
        self.assertEqual(state["city"], "ANKARA")

    def test_retry_loop_clears_the_province_after_a_failure(self):
        """`scrape_shell_data` hata sonrası ili unutmalı ki baştan seçilsin."""
        import shell_bot

        seen = []

        def fake_scrape_target(page, city, district, column_map, state):
            seen.append((city, district, state.get("city")))
            raise RuntimeError("boom")

        targets = [{"il": "ISTANBUL", "ilce": "KADIKOY"},
                   {"il": "ISTANBUL", "ilce": "BESIKTAS"}]
        with unittest.mock.patch.object(shell_bot, "_scrape_target", fake_scrape_target), \
                unittest.mock.patch.object(shell_bot, "sync_playwright", _FakePlaywright), \
                unittest.mock.patch.object(shell_bot, "_limited_targets", lambda t: t), \
                unittest.mock.patch.object(shell_bot, "_settle", lambda *a, **k: None):
            shell_bot.scrape_shell_data(targets)

        # Her denemeye girerken state temiz olmalı; "ISTANBUL" olarak
        # kalsaydı ikinci hedef ili hiç seçmeden bayat listede arardı.
        self.assertTrue(all(previous is None for _, _, previous in seen), seen)


class _FakePage:
    def goto(self, *args, **kwargs):
        return None


class _FakeBrowser:
    def new_page(self, **kwargs):
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
