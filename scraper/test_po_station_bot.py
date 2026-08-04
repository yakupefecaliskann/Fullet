"""Petrol Ofisi envanter botunun kendine ozgu parse mantiginin kilidi (F4-3).

Ortak suzgecler (karantina, il dogrulama) `test_station_inventory_common`'da.
Burada yalnizca PO'ya ozgu risk test edilir: veri bir API'den degil, 3,1 MB'lik
bir HTML sayfasina GOMULU JSON'dan cikariliyor. Sayfa bicimi degisirse bot
sessizce bos donebilir; cikarim mantigi kirilgandir ve kilitlenmelidir.
"""
from __future__ import annotations

import unittest

import po_station_bot as bot


class GomuluJsonCikarimTest(unittest.TestCase):
    """Sayfadan istasyon nesnelerini cikarma.

    Canli olcum (4 Agustos 2026): sayfada 7.869 nesne var ama yalnizca 2.623
    benzersiz `Id`. Sayfa il il bolunmus dizilerde ayni istasyonu birden fazla
    kez tasiyor — tekillestirme sart, yoksa 3 kat kayit yazilir.
    """

    def test_tek_nesne_cikarilir(self):
        html = '<script>var x = [{"Id":1,"StationName":"A","Latitude":40.1}];</script>'
        kayitlar = bot._sayfadan_istasyonlari_cikar(html)
        self.assertEqual(len(kayitlar), 1)
        self.assertEqual(kayitlar[0]["StationName"], "A")

    def test_tekrar_eden_id_tekillestirilir(self):
        html = (
            '[{"Id":1,"StationName":"A"}]'
            '[{"Id":1,"StationName":"A"},{"Id":2,"StationName":"B"}]'
        )
        kayitlar = bot._sayfadan_istasyonlari_cikar(html)
        self.assertEqual(len(kayitlar), 2)
        self.assertEqual({k["Id"] for k in kayitlar}, {1, 2})

    def test_adresteki_susu_parantez_diziyi_bolmez(self):
        """Adres alanlarinda '{' gecebiliyor; string icindeyken sayilmamali."""
        html = '[{"Id":7,"StationName":"X","Address":"NO:1{ MAH."}]'
        kayitlar = bot._sayfadan_istasyonlari_cikar(html)
        self.assertEqual(len(kayitlar), 1)
        self.assertEqual(kayitlar[0]["Address"], "NO:1{ MAH.")

    def test_kacisli_tirnak_nesneyi_bolmez(self):
        html = r'[{"Id":8,"StationName":"A\"B","Address":"Y"}]'
        kayitlar = bot._sayfadan_istasyonlari_cikar(html)
        self.assertEqual(len(kayitlar), 1)
        self.assertEqual(kayitlar[0]["StationName"], 'A"B')

    def test_ic_ice_nesne_bozmaz(self):
        html = '[{"Id":9,"StationName":"A","Extra":{"k":{"n":1}},"Address":"Z"}]'
        kayitlar = bot._sayfadan_istasyonlari_cikar(html)
        self.assertEqual(len(kayitlar), 1)
        self.assertEqual(kayitlar[0]["Address"], "Z")

    def test_bicim_degisirse_bos_doner_patlamaz(self):
        """Sayfa bicimi degisirse bot sessizce bos donmeli, exception atmamali.

        `scrape_data` bos listede hicbir sey yazmaz ve uyarir — boylece bozuk
        bir kazima mevcut envanteri silmez.
        """
        self.assertEqual(bot._sayfadan_istasyonlari_cikar("<html>bos</html>"), [])
        self.assertEqual(bot._sayfadan_istasyonlari_cikar(""), [])

    def test_kapanmamis_nesne_atlanir(self):
        html = '[{"Id":5,"StationName":"KAPANMAMIS"'
        self.assertEqual(bot._sayfadan_istasyonlari_cikar(html), [])

    def test_idsiz_nesne_alinmaz(self):
        html = '[{"Id":null,"StationName":"A"}]'
        self.assertEqual(bot._sayfadan_istasyonlari_cikar(html), [])


class MarkaAdiTest(unittest.TestCase):
    def test_marka_kanonik_yazimla_ayni(self):
        """`Petrol Ofisi` yazimi BRAND_ALIASES'in kanonik degeriyle uyusmali;
        ayrisirsa istasyonlar fiyat kayitlariyla eslesmez."""
        from normalization import normalize_brand
        self.assertEqual(normalize_brand(bot.BRAND), bot.BRAND)


if __name__ == "__main__":
    unittest.main()
