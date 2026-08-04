"""3 Ağustos 2026 temizlik operasyonunda bulunan hataların regresyon kilidi.

Bu dosyadaki her testin arkasında CANLI VERİDE ölçülmüş bir arıza var.
Hiçbiri varsayımsal değil — hepsi bir kez gerçekten oldu.
"""

from __future__ import annotations

import ast
import pathlib
import re
import unittest

import matching
import merge_duplicate_stations as merger

SCRAPER_DIR = pathlib.Path(__file__).resolve().parent


def _station(station_id, *, brand="Shell", name="TEST", lat=39.9, lon=32.8, active=True):
    return {
        "id": station_id,
        "marka": brand,
        "isim": name,
        "aktif": active,
        "olusturulma_tarihi": "2026-05-01T00:00:00+00:00",
        "_coord": (lat, lon),
    }


class PassiveDuplicateTest(unittest.TestCase):
    """A1: pasif üyeli kopya çiftleri görülmeliydi, görülmüyordu.

    F3-1 "101 kopya -> 0" diye kapatılmıştı. Ama `merge_duplicate_stations`
    yalnızca AKTİF istasyonları kümeliyordu; çiftin bir üyesi o an pasifse
    çift hiç görülmüyordu. Sonra fiyat yazma yolu (`istasyonlar.aktif = True`)
    o kaydı diriltince kopya AKTİF olarak geri geliyordu. Canlıda 26 çift.
    """

    def test_passive_member_does_not_hide_the_pair(self):
        stations = [
            _station("aktif-olan", name="ÇİNÇİN.", lat=39.9000, lon=32.8000),
            _station("pasif-olan", name="Shell", lat=39.9001, lon=32.8000, active=False),
        ]
        clusters = merger._find_clusters(stations)
        self.assertEqual(len(clusters), 1, "pasif üyeli çift kümelenmeliydi")
        self.assertEqual(len(clusters[0]), 2)

    def test_active_record_survives_over_passive(self):
        """Hayatta kalan DAİMA aktif olan olmalı.

        Aksi hâlde canlı kayıt silinip ölü kayıt bırakılırdı — kullanıcı
        istasyonu haritada tamamen kaybederdi.
        """
        passive_real_name = _station("pasif", name="GERÇEK AD", active=False)
        active_generic = _station("aktif", name="Shell", active=True)
        survivor = merger._pick_survivor([passive_real_name, active_generic], {})
        self.assertEqual(survivor["id"], "aktif")

    def test_real_name_is_rescued_onto_generic_survivor(self):
        """Aktiflik isim kalitesinden önce geldiği için hayatta kalan jenerik
        adlı olabiliyor; gerçek ad kaybolmamalı."""
        cluster = [
            _station("aktif", name="Shell", active=True),
            _station("pasif", name="ÇEKMEKÖY AKÇEŞME.", active=False),
        ]
        survivor = merger._pick_survivor(cluster, {})
        self.assertEqual(merger._better_name(cluster, survivor), "ÇEKMEKÖY AKÇEŞME.")

    def test_non_generic_survivor_keeps_its_own_name(self):
        cluster = [
            _station("a", name="HANDERESİ.", active=True),
            _station("b", name="BAŞKA AD", active=False),
        ]
        survivor = merger._pick_survivor(cluster, {})
        self.assertIsNone(merger._better_name(cluster, survivor))


class VisibilityConsistencyTest(unittest.TestCase):
    """A3: `aktif` ve `visibility_status` birbiriyle çelişiyordu.

    Canlıda 232 satır "aktif ama hidden", 354 satır "pasif ama visible"ydı.
    `_station_inventory_target` insert'i `aktif=False` yazarken görünürlüğü
    hiç yazmıyordu ve kolon varsayılanı 'visible'dı.
    """

    def test_inactive_insert_is_always_hidden(self):
        source = (SCRAPER_DIR / "matching.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == "_station_inventory_target"
        )
        inserted_keys = set()
        has_inactive = False
        for node in ast.walk(function):
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if not isinstance(key, ast.Constant):
                        continue
                    inserted_keys.add(key.value)
                    if key.value == "aktif" and getattr(value, "value", None) is False:
                        has_inactive = True
        self.assertTrue(has_inactive, "insert hâlâ aktif=False yazmalı")
        self.assertIn(
            "visibility_status", inserted_keys,
            "aktif=False yazan insert visibility_status'ü de yazmalı, "
            "yoksa kolon varsayılanı 'visible' ile çelişir",
        )


class PaginationOrderTest(unittest.TestCase):
    """A5: `ORDER BY` olmadan sayfalama satır kaybettirir.

    Postgres sırayı garanti etmez; botlar bu tablolara sürekli yazdığı için
    satırlar heap'te yer değiştirir ve bir satır iki sayfada gelebilir ya da
    hiç gelmeyebilir. Depoda 9 sayfalama bu hatayı taşıyordu.
    """

    @staticmethod
    def _chain_has_order(node: ast.AST) -> bool:
        while isinstance(node, (ast.Call, ast.Attribute)):
            if isinstance(node, ast.Attribute):
                if node.attr == "order":
                    return True
                node = node.value
            else:
                node = node.func
        return False

    def test_every_paginated_query_orders_first(self):
        offenders = []
        for path in sorted(SCRAPER_DIR.glob("*.py")):
            if path.name.startswith("test_"):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "range"
                    and not self._chain_has_order(node.func.value)
                ):
                    offenders.append(f"{path.name}:{node.lineno}")
        self.assertEqual(
            offenders, [],
            "ORDER BY'sız sayfalama bulundu (satır kaybı riski): "
            + ", ".join(offenders),
        )


class ProximityIdentityTest(unittest.TestCase):
    """Kimlik marka + KONUM'dur; idari alanlar (il/ilce) kimliğe girmez.

    Eski kova anahtarı `round(coord, 4)` (~11 m) kullanıyordu ve aynı
    istasyonun 12 m farklı iki kaydı ayrı sanılıyordu.
    """

    def test_same_place_different_district_is_the_same_station(self):
        index = matching.StationProximityIndex()
        index.add("Shell", 39.90000, 32.80000, "asil")
        # 12 m ötede, ilçesi farklı yazılmış aynı istasyon.
        self.assertEqual(index.find("Shell", 39.90011, 32.80000), "asil")

    def test_different_brand_is_never_the_same_station(self):
        index = matching.StationProximityIndex()
        index.add("Shell", 39.9, 32.8, "shell-kaydi")
        self.assertIsNone(index.find("Opet", 39.9, 32.8))

    def test_beyond_radius_is_a_separate_station(self):
        """75-150 m bandı KASTEN birleştirilmez: 'YAĞLI BATI'/'YAĞLI DOĞU'
        gibi yol ayrımının iki yanındaki AYRI istasyonlar oradadır."""
        index = matching.StationProximityIndex()
        index.add("Shell", 39.90000, 32.80000, "bati")
        self.assertIsNone(index.find("Shell", 39.90100, 32.80000))  # ~111 m


class LowPriorityTrapTest(unittest.TestCase):
    """4 Ağustos 2026: `low_priority` tek yönlü bir kapandı.

    Canlıda 989 aktif istasyon (aktiflerin %36,6'sı) `low_priority` damgalıydı
    ve HEPSİNİN gösterilebilir fiyatı vardı — TotalEnergies'in %95'i dahil.
    Damga `database_writes.py`'nin eski koşulsuz yazımından kalmaydı; yazma
    3 Ağustos'ta durdurulmuş ama moloz temizlenmemişti.

    Asıl arıza: `low_priority` -> `visible` geçişini yapan hiçbir mekanizma
    yoktu. JOB 5 yalnızca hidden<->visible, JOB 3 yalnızca visible->low_priority.
    Faz 3/madde 21 ile `low_priority` uygulamada gerçek etki kazanınca
    (`smart_station_service.dart` bu istasyonları "en ucuz" motorundan atıyor)
    989 istasyon sessizce fiyat karşılaştırmasından düştü.
    """

    SQL = (SCRAPER_DIR.parent / "database" / "auto_price_staleness.sql").read_text(
        encoding="utf-8"
    )

    # JOB 5 ve JOB 3'ün ORTAK tazelik yüklemi. İkisi de bunu kullanmak
    # ZORUNDA, yoksa istasyonlar visible <-> low_priority salınır.
    SHOWABLE = "price_status IN ('fresh', 'stale')"

    def _job_body(self, job_name):
        """Adı verilen cron job'ın $$...$$ gövdesini döndürür.

        Job adı dosyada yorumlarda da geçtiği için gövdeyi `cron.schedule`
        çağrısına sabitliyoruz; düz arama yanlış bloğu yakalıyordu.
        """
        pattern = (
            r"cron\.schedule\(\s*'" + re.escape(job_name) + r"'\s*,"
            r"\s*'[^']*'\s*,\s*\$\$(.*?)\$\$"
        )
        match = re.search(pattern, self.SQL, re.DOTALL)
        self.assertIsNotNone(
            match, f"{job_name} için cron.schedule bloğu bulunamadı"
        )
        return match.group(1)

    def test_return_lever_exists(self):
        """5d: fiyatı tazelenen low_priority istasyon visible'a dönmeli."""
        body = self._job_body("fullet-resolve-station-visibility")
        self.assertIn(
            "visibility_status = 'low_priority'", body,
            "JOB 5'te geri dönüş kolu (5d) yok: low_priority damgası kalıcı "
            "hale gelir ve istasyon fiyatı taze olsa bile 'en ucuz' "
            "yarışına giremez.",
        )

    def test_return_lever_and_demotion_use_the_same_predicate(self):
        """Simetri şart: aksi halde her gece düşüp her saat geri kalkarlar."""
        for job in ("fullet-resolve-station-visibility", "fullet-hide-stale-stations"):
            self.assertIn(
                self.SHOWABLE, self._job_body(job),
                f"{job} ortak tazelik yüklemini kullanmıyor. JOB 3 ve JOB 5d "
                "farklı yüklem kullanırsa istasyonlar visible <-> low_priority "
                "arasında salınır.",
            )

    def test_demotion_does_not_use_the_wrong_freshness_column(self):
        """JOB 3 `son_guncelleme`'ye bakmamalı — freshness.py'nin uyarısı.

        son_guncelleme = fiyatın son DEĞİŞTİĞİ an (Türkiye'de ayda birkaç kez)
        son_dogrulama  = fiyatı son DOĞRULADIĞIMIZ an (her koşuda)
        Eski yüklem yüzünden her gün doğrulanan fiyatlar "bayat" sanılıyordu.
        """
        body = self._job_body("fullet-hide-stale-stations")
        self.assertNotIn(
            "son_guncelleme", body,
            "JOB 3 yine `son_guncelleme` üzerinden tazelik ölçüyor; bu, doğru "
            "ama uzun süredir değişmemiş fiyatları bayat sayan hatadır.",
        )


if __name__ == "__main__":
    unittest.main()
