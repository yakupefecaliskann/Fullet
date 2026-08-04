"""F4-1 Opet envanter botunun regresyon kilidi.

Buradaki her testin arkasinda 4 Agustos 2026'da CANLI VERIDE olculmus bir
risk var. Hicbiri varsayimsal degil.
"""
from __future__ import annotations

import unittest

import matching
import opet_station_bot as bot
from matching import StationProximityIndex


class KarantinaBandiTest(unittest.TestCase):
    """Karantina bandi ile envanter yaricapi arasinda BOSLUK olmamali.

    Envanter yazma yolu 75 m icindekini "ayni istasyon" sayar. Bot da 75 m'yi
    alt sinir kabul eder. Bu iki sayi ayrisirsa arada yazilmayan bir bant
    olusur ve supheli kayit sessizce EKLENIR — yani kopya uretir.
    """

    def test_alt_sinir_envanter_yaricapiyla_ayni(self):
        self.assertAlmostEqual(
            bot.KARANTINA_ALT_KM * 1000,
            matching.STATION_MATCH_RADIUS_METERS,
            places=6,
            msg="Karantina alt siniri envanter eslestirme yaricapindan ayrildi; "
                "arada kalan kayitlar kopya olarak eklenir.",
        )

    def test_ust_sinir_alt_sinirdan_buyuk(self):
        self.assertGreater(bot.KARANTINA_UST_KM, bot.KARANTINA_ALT_KM)


class KarantinaKarariTest(unittest.TestCase):
    """<75 m yaz, 75 m - 1 km yazma, >1 km yaz.

    Canli olcum (Opet, 4 Agustos 2026):
        <75 m     387 kayit -> mevcut kayit guncellenir
        75m-1km    74 kayit -> SUPHELI, yazilmaz
        >1 km     785 kayit -> yeni istasyon, yazilir

    Ornek: API 'PURLU OTOMOTIV...' canli 'Opet Isparta Merkez'e 82 m uzakta.
    Ayni istasyon; korlemesine eklenseydi kopya olurdu.
    """

    BASE_LAT, BASE_LON = 39.90000, 32.80000

    def _indeksler(self):
        near = StationProximityIndex(radius_meters=bot.KARANTINA_ALT_KM * 1000)
        far = StationProximityIndex(radius_meters=bot.KARANTINA_UST_KM * 1000)
        for index in (near, far):
            index.add("Opet", self.BASE_LAT, self.BASE_LON, "mevcut")
        return near, far

    def _karar(self, lat, lon):
        """Botun karantina karari: 'yaz' | 'karantina'."""
        near, far = self._indeksler()
        if near.find("Opet", lat, lon):
            return "yaz"
        if far.find("Opet", lat, lon) is not None:
            return "karantina"
        return "yaz"

    def test_cok_yakin_kayit_yazilir(self):
        # ~11 m kuzey: kesinlikle ayni istasyon, guncellenmeli.
        self.assertEqual(self._karar(self.BASE_LAT + 0.0001, self.BASE_LON), "yaz")

    def test_supheli_bant_yazilmaz(self):
        # ~82 m: canlida olculen 'Opet Isparta Merkez' vakasi.
        self.assertEqual(
            self._karar(self.BASE_LAT + 0.00074, self.BASE_LON), "karantina"
        )

    def test_supheli_bandin_ust_ucu_yazilmaz(self):
        # ~700 m: hala belirsiz.
        self.assertEqual(
            self._karar(self.BASE_LAT + 0.0063, self.BASE_LON), "karantina"
        )

    def test_uzak_kayit_yeni_istasyon_olarak_yazilir(self):
        # ~2,2 km: kesinlikle ayri istasyon.
        self.assertEqual(self._karar(self.BASE_LAT + 0.02, self.BASE_LON), "yaz")

    def test_mevcut_kayit_yoksa_her_sey_yazilir(self):
        near = StationProximityIndex(radius_meters=bot.KARANTINA_ALT_KM * 1000)
        far = StationProximityIndex(radius_meters=bot.KARANTINA_UST_KM * 1000)
        self.assertIsNone(far.find("Opet", self.BASE_LAT, self.BASE_LON))
        self.assertIsNone(near.find("Opet", self.BASE_LAT, self.BASE_LON))


class IlDogrulamaTest(unittest.TestCase):
    """Kaynagin `province` alani her zaman il degil.

    Canli olcum (4 Agustos 2026, Opet API'sinin 1.246 kaydi): 3 kayitta il
    alani bozuktu ve ucu de yazilmis olsaydi kalici cop kayit uretecekti —
    hicbir il eslesmesine giremedikleri icin fiyat alamaz, sonsuza kadar
    `hidden` kalirlardi. Ikisi canliya sizdi ve elle temizlendi.

        il='TAYAKADIN YASSIOREN CADDE'  (cadde adi, ilce ARNAVUTKOY)
        il='CARSAMBA'                   (ilce adi il alaninda)
        il='ISTANBUL' ilce='MERKEZ'     (Istanbul'da MERKEZ ilcesi yok)
    """

    def test_gecerli_il_kabul_edilir(self):
        self.assertIn(bot.normalize_province("BOLU"), bot.PROVINCES)
        self.assertIn(bot.normalize_province("İstanbul"), bot.PROVINCES)

    def test_cadde_adi_il_sayilmaz(self):
        self.assertNotIn(
            bot.normalize_province("TAYAKADIN YASSIÖREN CADDE"), bot.PROVINCES
        )

    def test_ilce_adi_il_sayilmaz(self):
        self.assertNotIn(bot.normalize_province("ÇARŞAMBA"), bot.PROVINCES)

    def test_istanbul_ilce_listesi_bos_degil(self):
        """Liste bosalirsa TUM Istanbul kayitlari elenir — sessiz felaket."""
        self.assertGreater(len(bot._ISTANBUL_ILCELERI), 30)

    def test_istanbul_merkez_taninmaz(self):
        from normalization import normalize_city
        self.assertNotIn(normalize_city("MERKEZ"), bot._ISTANBUL_ILCELERI)

    def test_gercek_istanbul_ilcesi_taninir(self):
        from normalization import normalize_city
        self.assertIn(normalize_city("KADIKÖY"), bot._ISTANBUL_ILCELERI)


class KaynakKaydiTest(unittest.TestCase):
    """Kaynak `OFFICIAL_STATION_SOURCES`'ta olmali.

    `normalize_station_inventory_item` bu kumede olmayan kaynagi sessizce
    None dondurur; bot calisir, 1.172 kayit ceker ve HICBIRI yazilmaz.
    """

    def test_kaynak_resmi_envanter_kumesinde(self):
        from config import OFFICIAL_STATION_SOURCES
        self.assertIn(bot.SOURCE, OFFICIAL_STATION_SOURCES)

    def test_kaynak_bolgesel_fiyat_kumesinde_degil(self):
        """Envanter kaynagi fiyat kaynagi degildir; karistirilirsa istasyon
        kayitlari fiyat yazma yoluna girer."""
        from config import OFFICIAL_REGIONAL_SOURCES
        self.assertNotIn(bot.SOURCE, OFFICIAL_REGIONAL_SOURCES)


if __name__ == "__main__":
    unittest.main()
