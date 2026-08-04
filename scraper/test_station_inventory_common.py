"""Envanter botlarinin ortak guvenlik suzgeclerinin regresyon kilidi (F4).

Buradaki her testin arkasinda canli veride olculmus bir ariza var. Bu
suzgecler Opet (F4-1), Petrol Ofisi (F4-3) ve sonraki tum envanter
botlarinin ortak savunmasi — biri bozulursa hepsi bozulur.
"""
from __future__ import annotations

import unittest

import matching
import station_inventory_common as ortak
from normalization import normalize_city


class KarantinaBandiTest(unittest.TestCase):
    """Karantina bandi ile envanter yaricapi arasinda BOSLUK olmamali.

    Envanter yazma yolu 75 m icindekini "ayni istasyon" sayar. Bant da 75 m'yi
    alt sinir kabul eder. Bu iki sayi ayrisirsa arada yazilmayan bir bant
    olusur ve supheli kayit sessizce EKLENIR — yani kopya uretir.
    """

    def test_alt_sinir_envanter_yaricapiyla_ayni(self):
        self.assertAlmostEqual(
            ortak.KARANTINA_ALT_KM * 1000,
            matching.STATION_MATCH_RADIUS_METERS,
            places=6,
            msg="Karantina alt siniri envanter eslestirme yaricapindan ayrildi; "
                "arada kalan kayitlar kopya olarak eklenir.",
        )

    def test_ust_sinir_alt_sinirdan_buyuk(self):
        self.assertGreater(ortak.KARANTINA_UST_KM, ortak.KARANTINA_ALT_KM)


class KarantinaKarariTest(unittest.TestCase):
    """<75 m yaz, 75 m - 1 km yazma, >1 km yaz.

    Canli olcum (Opet, 4 Agustos 2026):
        <75 m     387 kayit -> mevcut kayit guncellenir
        75m-1km    74 kayit -> SUPHELI, yazilmaz
        >1 km     785 kayit -> yeni istasyon, yazilir

    Ornek: API 'PURLU OTOMOTIV...' canli 'Opet Isparta Merkez'e 82 m uzakta.
    Ayni istasyon; korlemesine eklenseydi kopya olurdu.
    """

    BASE_LAT, BASE_LON = 39.90000, 39.80000

    def _indeksler(self):
        return ortak.yakinlik_indeksleri([(self.BASE_LAT, self.BASE_LON)], "Opet")

    def _karar(self, lat, lon):
        near, far = self._indeksler()
        return "karantina" if ortak.karantinada_mi(near, far, "Opet", lat, lon) else "yaz"

    def test_cok_yakin_kayit_yazilir(self):
        # ~11 m: kesinlikle ayni istasyon, yazma yolu gunceller.
        self.assertEqual(self._karar(self.BASE_LAT + 0.0001, self.BASE_LON), "yaz")

    def test_supheli_bant_yazilmaz(self):
        # ~82 m: canlida olculen 'Opet Isparta Merkez' vakasi.
        self.assertEqual(
            self._karar(self.BASE_LAT + 0.00074, self.BASE_LON), "karantina"
        )

    def test_supheli_bandin_ust_ucu_yazilmaz(self):
        # ~700 m: hala belirsiz.
        self.assertEqual(self._karar(self.BASE_LAT + 0.0063, self.BASE_LON), "karantina")

    def test_uzak_kayit_yeni_istasyon_olarak_yazilir(self):
        # ~2,2 km: kesinlikle ayri istasyon.
        self.assertEqual(self._karar(self.BASE_LAT + 0.02, self.BASE_LON), "yaz")

    def test_mevcut_kayit_yoksa_her_sey_yazilir(self):
        near, far = ortak.yakinlik_indeksleri([], "Opet")
        self.assertFalse(
            ortak.karantinada_mi(near, far, "Opet", self.BASE_LAT, self.BASE_LON)
        )

    def test_farkli_marka_karantinaya_sokmaz(self):
        """Yakinlik marka icinde anlamlidir; Shell'in yanindaki Opet kopya degil."""
        near, far = self._indeksler()
        self.assertFalse(
            ortak.karantinada_mi(
                near, far, "Shell", self.BASE_LAT + 0.00074, self.BASE_LON
            )
        )


class KonumDogrulamaTest(unittest.TestCase):
    """Kaynagin il alani her zaman il degil.

    Canli olcum: Opet API'sinin 1.246 kaydindan 3'unde il alani bozuktu ve
    ucu de yazilsaydi kalici cop kayit uretecekti — hicbir il eslesmesine
    giremedikleri icin fiyat alamaz, sonsuza kadar `hidden` kalirlardi.
    Ikisi canliya sizdi ve elle temizlendi.

        il='TAYAKADIN YASSIOREN CADDE'  (cadde adi, ilce ARNAVUTKOY)
        il='CARSAMBA'                   (ilce adi il alaninda)
        il='ISTANBUL' ilce='MERKEZ'     (Istanbul'da MERKEZ ilcesi yok)
    """

    def test_gecerli_il_kabul_edilir(self):
        self.assertTrue(ortak.gecerli_konum("BOLU", "MERKEZ"))
        self.assertTrue(ortak.gecerli_konum("Edirne", "MERİÇ"))

    def test_cadde_adi_il_sayilmaz(self):
        self.assertFalse(ortak.gecerli_konum("TAYAKADIN YASSIÖREN CADDE", "ARNAVUTKÖY"))

    def test_ilce_adi_il_sayilmaz(self):
        self.assertFalse(ortak.gecerli_konum("ÇARŞAMBA", "BEŞİKTAŞ"))

    def test_istanbul_taninmayan_ilce_reddedilir(self):
        self.assertFalse(ortak.gecerli_konum("İstanbul", "MERKEZ"))

    def test_istanbul_gercek_ilcesi_kabul_edilir(self):
        self.assertTrue(ortak.gecerli_konum("İstanbul", "KADIKÖY"))

    def test_istanbul_ilce_listesi_bos_degil(self):
        """Liste bosalirsa TUM Istanbul kayitlari elenir — sessiz felaket."""
        self.assertGreater(len(ortak.ISTANBUL_ILCELERI), 30)
        self.assertIn(normalize_city("BEŞİKTAŞ"), ortak.ISTANBUL_ILCELERI)


class KaynakKaydiTest(unittest.TestCase):
    """Envanter kaynaklari dogru kumede olmali.

    `normalize_station_inventory_item` OFFICIAL_STATION_SOURCES'ta olmayan
    kaynagi sessizce None dondurur: bot calisir, binlerce kayit ceker ve
    HICBIRI yazilmaz. Fiyat kumesine karismasi ise istasyon kayitlarini
    fiyat yazma yoluna sokar.
    """

    def _botlar(self):
        import opet_station_bot
        import po_station_bot
        return (opet_station_bot, po_station_bot)

    def test_kaynaklar_envanter_kumesinde(self):
        from config import OFFICIAL_STATION_SOURCES
        for bot in self._botlar():
            self.assertIn(bot.SOURCE, OFFICIAL_STATION_SOURCES, bot.__name__)

    def test_kaynaklar_bolgesel_fiyat_kumesinde_degil(self):
        from config import OFFICIAL_REGIONAL_SOURCES
        for bot in self._botlar():
            self.assertNotIn(bot.SOURCE, OFFICIAL_REGIONAL_SOURCES, bot.__name__)

    def test_botlar_run_all_bots_listesinde(self):
        """Liste disinda kalan bot hic kosmaz; envanter sessizce bayatlar."""
        import run_all_bots
        for beklenen in ("opet_station_bot.py", "po_station_bot.py"):
            self.assertIn(beklenen, run_all_bots.STATION_BOTS)


if __name__ == "__main__":
    unittest.main()
