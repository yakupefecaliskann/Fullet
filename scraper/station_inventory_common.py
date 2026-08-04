"""Envanter botlarinin ortak guvenlik suzgecleri (F4).

Opet (F4-1) ve Petrol Ofisi (F4-3) botlari ayni uc arizaya karsi ayni
korumaya ihtiyac duyuyor. Ucu de canli veride olculdu, hicbiri varsayimsal
degil:

1. KARANTINA BANDI — envanter yazma yolu 75 m icindekini "ayni istasyon"
   sayip GUNCELLER, disindakini EKLER. Bu ikili karar yetmiyor: canlida
   75 m - 1 km bandinda, eski kaydin koordinati kaba oldugu icin eslesmeyen
   ama aslinda AYNI olan istasyonlar var (82 m'de 'Opet Isparta Merkez').
   Korlemesine eklemek kopya uretir. 75 m yaricapini buyutmek ise
   ProximityIdentityTest'in korudugu ayrimi bozar ("YAGLI BATI"/"YAGLI DOGU"
   gibi yol ayriminin iki yanindaki AYRI istasyonlar). Cozum: belirsiz bandi
   hic yazmamak.

2. IL DOGRULAMASI — kaynagin il alani her zaman il degil. Opet API'sinde
   3 kayitta cadde/ilce adi vardi ("TAYAKADIN YASSIOREN CADDE"). Boyle bir
   kayit hicbir il eslesmesine giremez, fiyat alamaz ve sonsuza kadar
   `hidden` kalir — sessiz cop kayit.

3. ISTANBUL ILCE DOGRULAMASI — fiyat yolu Istanbul'u ANADOLU/AVRUPA
   bolgelerine ayirir. Bu iki listenin disinda kalan ilce (canlida "MERKEZ")
   hicbir bolgeye giremez; `_reset_split_region_targets` onu pasiflestirir
   ve bir daha aktiflestirmez.
"""
from __future__ import annotations

from typing import Any, Iterable

from config import ISTANBUL_REGION_DISTRICTS
from matching import StationProximityIndex, _haversine
from normalization import PROVINCES, normalize_city, normalize_province

# Karantina bandinin ALT siniri envanter yazma yolunun yaricapiyla AYNI
# olmali (matching.STATION_MATCH_RADIUS_METERS = 75 m). Ayrisirlarsa arada
# yazilmayan bir bosluk kalir ve supheli kayit sessizce eklenir.
KARANTINA_ALT_KM = 0.075
KARANTINA_UST_KM = 1.0

ISTANBUL_ILCELERI = frozenset(
    ilce for bolge in ISTANBUL_REGION_DISTRICTS.values() for ilce in bolge
)


def gecerli_konum(il_ham: Any, ilce_ham: Any) -> bool:
    """Il 81 il listesinde mi? Istanbul ise ilce taniniyor mu?"""
    il = normalize_province(il_ham)
    if il not in PROVINCES:
        return False
    if il == "ISTANBUL" and normalize_city(ilce_ham) not in ISTANBUL_ILCELERI:
        return False
    return True


def yakinlik_indeksleri(
    live_points: Iterable[tuple[float, float]], brand: str
) -> tuple[StationProximityIndex, StationProximityIndex]:
    """(75 m indeksi, 1 km indeksi).

    Hucre boyutu 0,01 derece (~1,1 km) ve komsu hucreler de tarandigi icin
    1 km yaricap bu indekste guvenle calisir.
    """
    near = StationProximityIndex(radius_meters=KARANTINA_ALT_KM * 1000)
    far = StationProximityIndex(radius_meters=KARANTINA_UST_KM * 1000)
    for latitude, longitude in live_points:
        near.add(brand, latitude, longitude, "x")
        far.add(brand, latitude, longitude, "x")
    return near, far


def karantinada_mi(
    near: StationProximityIndex,
    far: StationProximityIndex,
    brand: str,
    latitude: float,
    longitude: float,
) -> bool:
    """Kayit belirsiz bantta mi? True ise YAZILMAMALI.

    <75 m  -> False (ayni istasyon, yazma yolu gunceller)
    75m-1km -> True  (belirsiz, karantina)
    >1 km  -> False (kesinlikle yeni istasyon)
    """
    if near.find(brand, latitude, longitude):
        return False
    return far.find(brand, latitude, longitude) is not None


def en_yakin_metre(
    live_points: list[tuple[float, float]], latitude: float, longitude: float
) -> float:
    """Raporlama icin en yakin canli kayda mesafe (metre)."""
    if not live_points:
        return float("inf")
    return min(
        _haversine(latitude, longitude, lat, lon) * 1000 for lat, lon in live_points
    )


def rapor_yaz(bozuk_il: list, karantina: list) -> None:
    """Iki suzgecin sonucunu tek bicimde bastirir."""
    if bozuk_il:
        print(f"[BOZUK IL] {len(bozuk_il)} kayit YAZILMADI (il alani 81 il "
              f"listesinde degil veya Istanbul ilcesi taninmiyor; fiyat "
              f"eslesmesine giremez, cop kayit olurdu):")
        for il, ilce, isim in bozuk_il[:5]:
            print(f"           il={str(il)[:30]!r} ilce={str(ilce)[:18]!r} "
                  f"{str(isim)[:32]!r}")
        if len(bozuk_il) > 5:
            print(f"           ... ve {len(bozuk_il) - 5} kayit daha")

    if karantina:
        print(f"[KARANTINA] {len(karantina)} supheli kayit YAZILMADI "
              f"({KARANTINA_ALT_KM * 1000:.0f}-{KARANTINA_UST_KM * 1000:.0f} m "
              f"bandinda mevcut bir kayda yakin). Zenginlestirme adayi.")
        for mesafe, isim, il in sorted(karantina)[:8]:
            print(f"             {mesafe:6.0f} m  {str(isim)[:42]!r} ({il})")
        if len(karantina) > 8:
            print(f"             ... ve {len(karantina) - 8} kayit daha")
