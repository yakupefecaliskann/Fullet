"""Shell envanter botunun kendine ozgu iki kirilma noktasinin kilidi (F4-6).

Ortak suzgecler (karantina, il dogrulama) `test_station_inventory_common`'da.
Burada yalnizca Shell'e ozgu iki risk test edilir; ikisi de CANLIDA gerceklesti:

1. PROP KABUGU — find.shell.com Agustos 2026'da Inertia.js'e gecti, proplar
   `data-react-props` OZNITELIGINDEN `<script type="application/json">`
   blogunun icine tasindi. Eski ayristirici tanimadigi bicimde SESSIZCE bos
   sozluk donuyordu; bot 3 hafta boyunca 0 kayitla basarisiz oldu ve gunlukte
   sebebi soyleyen tek satir yoktu.

2. ADRESTEN IL CIKARIMI — eski surum adresin TAMAMINI tek parca tarayip en
   uzun il adini nerede gecerse kabul ediyordu. Turkiye'de caddeler komsu
   illerin adini tasir, dolayisiyla 42 istasyon YANLIS ILDE duruyordu ve kendi
   ilinin degil, cadde adindaki ilin fiyatini aliyordu.
"""
from __future__ import annotations

import json
import unittest

import shell_station_bot as bot


class PropKabuguTest(unittest.TestCase):
    """Iki tasima bicimi de taninmali; hicbiri yoksa SESSIZ KALINMAMALI."""

    def test_inertia_script_blogu_okunur(self):
        """Kaynagin bugunku bicimi (Agustos 2026 sonrasi)."""
        payload = {"component": "Locations", "props": {"geographicListProps": {"a": 1}}}
        html = f'<script data-page="app" type="application/json">{json.dumps(payload)}</script>'
        self.assertEqual(bot._page_props(html), {"geographicListProps": {"a": 1}})

    def test_eski_oznitelik_bicimi_hala_okunur(self):
        """Eski bicim bazi yerel surumlerde donebiliyor; maliyeti tek satir."""
        html = '<div data-react-props="{&quot;stationListProps&quot;:{&quot;b&quot;:2}}"></div>'
        self.assertEqual(bot._page_props(html), {"stationListProps": {"b": 2}})

    def test_bicim_taninmazsa_HATA_firlatir(self):
        """Regresyon kilidi: burada sessizce {} donmek 3 haftalik ariza uretti.

        Bos sozluk donmek `_locations_index`'i bos listeye, onu da "0 istasyon"
        sonucuna goturuyor. Sonuc gorunurde ayni (bot basarisiz) ama sebebi
        gunluge HIC yazilmiyor — arizanin kaynak degisikligi mi yoksa ag
        sorunu mu oldugu anlasilamiyor.
        """
        with self.assertRaises(bot.SayfaBicimiDegisti):
            bot._page_props("<html><body>bakim calismasi</body></html>")

    def test_script_govdesi_html_kacisi_COZULMEZ(self):
        """Script govdesi HAM JSON'dur.

        Oznitelik bicimi HTML kacisli oldugu icin `html.unescape` sart, ama
        ayni islemi script govdesine uygulamak veri icindeki duz bir "&amp;"
        dizisini "&" yapip adresi bozardi.
        """
        payload = {"props": {"location": {"name": "A&amp;B"}}}
        html = f'<script type="application/json">{json.dumps(payload)}</script>'
        self.assertEqual(bot._page_props(html)["location"]["name"], "A&amp;B")


class AdrestenIlCikarimiTest(unittest.TestCase):
    """Canli olculen 42 hatanin uctan uca kilidi.

    Her ornek gercek bir Shell adresidir; parantez icindeki il, eski surumun
    urettigi YANLIS sonuctur. Bagimsiz dogrulama: 42 istasyonun da 15 km
    icindeki en yakin RAKIP marka istasyonunun ili, burada beklenen ille
    ortusuyor (25.08.2026 olcumu).
    """

    def test_caddedeki_il_adi_gercek_ili_govdelemez(self):
        ornekler = [
            # (adres, beklenen il, beklenen ilce, eski hatali il)
            ("ANKARA ASFALTI YANYOL 21, 34860, KARTAL ISTANBUL, TR",
             "ISTANBUL", "KARTAL", "ANKARA"),
            ("SIVAS CAD. 13/B, 66300, AKDAGMADENI  YOZGAT, TR",
             "YOZGAT", "AKDAGMADENI", "SIVAS"),
            ("IZMIR CANAKKALE YOLU BLV. 335, 10280, AYVALIK BALIKESIR, TR",
             "BALIKESIR", "AYVALIK", "CANAKKALE"),
            ("SILIFKE-ANTALYA CADDESI 191/A, 33500, BOZYAZI MERSIN, TR",
             "MERSIN", "BOZYAZI", "ANTALYA"),
            ("YALOVA YOLU CADDESI 231/1, 16000, GEMLIK BURSA, TR",
             "BURSA", "GEMLIK", "YALOVA"),
        ]
        for adres, il, ilce, eski in ornekler:
            with self.subTest(adres=adres):
                self.assertEqual(bot._city_district_from_text(adres), (il, ilce))
                self.assertNotEqual(bot._city_district_from_text(adres)[0], eski)

    def test_ayni_il_iki_kez_gecerse_SONDAKI_alinir(self):
        """"IZMIR ANKARA ASFALTI ... KEMALPASA IZMIR" -> IZMIR/KEMALPASA."""
        self.assertEqual(
            bot._city_district_from_text("IZMIR ANKARA ASFALTI CAD 18, 35730, KEMALPASA IZMIR, TR"),
            ("IZMIR", "KEMALPASA"),
        )

    def test_merkez_ilcede_ilce_bos_kalir(self):
        """Merkez adresleri yalnizca il adini tasir; uydurma ilce URETILMEZ."""
        self.assertEqual(
            bot._city_district_from_text("ATATURK BULVARI. 12, 02000, ADIYAMAN, TR"),
            ("ADIYAMAN", ""),
        )

    def test_bolge_adi_ilce_il_kalibini_cozer(self):
        """Bolge sayfasi adi ikinci kaynaktir; ilceyi o tamamlar."""
        self.assertEqual(bot._city_district_from_text("MERKEZ ADIYAMAN"), ("ADIYAMAN", "MERKEZ"))
        self.assertEqual(bot._city_district_from_text("19 MAYIS SAMSUN"), ("SAMSUN", "19 MAYIS"))
        self.assertEqual(bot._city_district_from_text("ACIGOL - NEVSEHIR"), ("NEVSEHIR", "ACIGOL"))

    def test_il_yoksa_bos_doner(self):
        """Uydurmaktansa bos donmek dogru: `gecerli_konum` kaydi eler."""
        self.assertEqual(bot._city_district_from_text("SAIR NEDIM CAD., 34330, AKARETLER BESIKTAS, TR"), ("", ""))
        self.assertEqual(bot._city_district_from_text(""), ("", ""))
        self.assertEqual(bot._city_district_from_text(None), ("", ""))

    def test_posta_kodu_ilce_adina_karismaz(self):
        il, ilce = bot._city_district_from_text("MAH. 5, 34860, KARTAL ISTANBUL, TR")
        self.assertEqual((il, ilce), ("ISTANBUL", "KARTAL"))
        self.assertNotIn("34860", ilce)


class DetayIlceTamamlamaTest(unittest.TestCase):
    """Adres ilceyi vermezse bolge adindan tamamlanir — ama ayni ilse."""

    def _detay(self, adres, grup_adi, monkey):
        props = {"location": {
            "location_id": "1", "name": "X", "formatted_address": adres,
            "lat": 40.0, "lng": 30.0,
        }}
        monkey(props)
        return bot._parse_station_detail({
            "url": "https://find.shell.com/tr/fuel/1-x/tr_TR",
            "group_name": grup_adi,
            "list_name": "X",
            "list_address": adres,
        })

    def setUp(self):
        self._gercek = bot._page_props

    def tearDown(self):
        bot._page_props = self._gercek

    def _sabitle(self, props):
        bot._get = lambda url: ""
        bot._page_props = lambda text: props

    def test_bos_ilce_bolge_adindan_tamamlanir(self):
        kayit = self._detay("ATATURK BULVARI. 12, 02000, ADIYAMAN, TR",
                            "MERKEZ ADIYAMAN", self._sabitle)
        self.assertEqual((kayit["il"], kayit["ilce"]), ("ADIYAMAN", "MERKEZ"))

    def test_farkli_ildeki_bolge_adi_ilceyi_TASIMAZ(self):
        """Bolge, istasyonun il sinirinin otesine baglanmis olabilir.

        Adres ILI kesindir; baska bir ilin ilcesini ona yapistirmak, istasyonu
        var olmayan bir (il, ilce) ciftine sokup fiyatsiz birakirdi.
        """
        kayit = self._detay("ATATURK BULVARI. 12, 02000, ADIYAMAN, TR",
                            "MERKEZ MALATYA", self._sabitle)
        self.assertEqual((kayit["il"], kayit["ilce"]), ("ADIYAMAN", ""))

    def test_adres_ili_vermezse_bolge_adi_devralir(self):
        kayit = self._detay("SAIR NEDIM CAD., 34330, AKARETLER BESIKTAS, TR",
                            "BESIKTAS ISTANBUL", self._sabitle)
        self.assertEqual((kayit["il"], kayit["ilce"]), ("ISTANBUL", "BESIKTAS"))


class DizinKapsamasiTest(unittest.TestCase):
    """Bolge sayfalarinin cogu dusserse YARIM envanter yazilmamali.

    Yarim yazmak, silmekten beter: eksik istasyonlar `aktif` kalir ama
    koordinatlari guncellenmez ve hangi kosunun eksik oldugu bir daha
    anlasilmaz. Bot bunun yerine basarisiz olur ve alarm acar.
    """

    def setUp(self):
        self._index = bot._locations_index
        self._links = bot._station_links

    def tearDown(self):
        bot._locations_index = self._index
        bot._station_links = self._links

    def test_esigin_altinda_kalan_kosu_HATA_firlatir(self):
        bot._locations_index = lambda: [
            {"name": "A", "url": "u1", "count": 100},
            {"name": "B", "url": "u2", "count": 100},
        ]

        def kirik_links(page):
            if page["name"] == "A":
                return [{"group_name": "A", "url": f"s{i}", "list_name": "X",
                         "list_address": ""} for i in range(50)]
            raise RuntimeError("500 Server Error")

        bot._station_links = kirik_links
        with self.assertRaises(bot.SayfaBicimiDegisti):
            bot._ham_kayitlari_topla()

    def test_esigin_ustunde_kalan_kosu_devam_eder(self):
        bot._locations_index = lambda: [{"name": "A", "url": "u1", "count": 10}]
        bot._station_links = lambda page: [
            {"group_name": "A", "url": f"s{i}", "list_name": "X", "list_address": ""}
            for i in range(9)
        ]
        bot._parse_station_detail = lambda station: {"marka": "Shell", "il": "ANKARA"}
        try:
            self.assertEqual(len(bot._ham_kayitlari_topla()), 9)
        finally:
            del bot._parse_station_detail


if __name__ == "__main__":
    unittest.main()
