"""Başlık metnine göre yakıt kolonu çözümleme.

Sabit kolon indeksleri, Fullet'in en pahalı veri hatası sınıfıydı: kaynak
tabloya bir kolon eklendiğinde ya da bir hücre boş geldiğinde bot sessizce
YANLIŞ ürünün fiyatını yazıyordu. Somut örnek (yol haritası S1-1):

    shell_bot: "LPG": _price_at(cols, 12) or _price_at(cols, 10)

    [12] "Otogaz (TL/Lt) Shell Autogas LPG"        <- gerçek LPG, çoğu ilçede "-"
    [10] "Yüksek Kükürtlü Fuel Oil (TL/Kg)"        <- `or` fallback'inin okuduğu

Sonuç: kilogram başına fuel oil fiyatı (38,51) litre başına LPG diye yazıldı;
Shell LPG ortalaması diğer markalardan %20 yukarıda çıktı (37,68 vs 31,3).

Bu modül iki savunma katmanı uygular:

1. **Birim kapısı** — kanonik yakıtlarımızın hepsi litre bazlıdır. Başlığında
   "/kg" geçen bir kolon asla yakıt kolonu sayılmaz. Tek başına bu kural
   yukarıdaki hatayı engellerdi.
2. **Anlamsal eşleme** — kolon, başlık metni `normalize_fuel`'den geçirilerek
   seçilir. Eşleşmeyen kolon okunmaz; tahmin yapılmaz.

Aynı yakıt için birden çok kolon varsa (standart + premium ürün) tercih sırası
korunur: **standart önce, premium fallback**. Premium ürünü olan ama standart
kolonu boş bırakan kaynaklarda (Shell) davranış eskisiyle aynı kalır; premium
kolonu yanlışlıkla tercih edilmez.
"""

from __future__ import annotations

import re
from typing import Callable, Iterable, Sequence

from config import CITY_REPLACEMENTS
from normalization import clean_text, normalize_fuel, parse_price

# Hücrede birden fazla sayı olabilir. Petrol Ofisi/BP hücreleri hem KDV dahil
# hem KDV hariç fiyatı taşır ("67.18 55.99 TL/LT +KDV") — pompada ödenen
# tutar İLK sayıdır. Bu yüzden hücrenin tamamını değil, ilk sayı benzeri
# parçayı ayrıştırıyoruz.
_CELL_NUMBER_RE = re.compile(r"\d{1,3}[.,]\d{2,3}")


def first_price_in_cell(cell: object) -> float | None:
    """Hücredeki ilk sayıyı fiyat olarak ayrıştırır ('-' ve boş hücre -> None)."""
    match = _CELL_NUMBER_RE.search(clean_text(cell))
    return parse_price(match.group(0)) if match else None

# Premium/özel ürün işaretleri. Bu kelimeleri taşıyan kolonlar aynı yakıtın
# standart kolonundan SONRA denenir (tamamen elenmez — kaynağın tek kolonu
# premium ürünse yine de kullanılır, örn. Petrol Ofisi "V/Max Kurşunsuz 95").
PREMIUM_MARKERS = (
    "v-power", "vpower", "v power", "v/max", "vmax", "vp ",
    "ultimate", "excellium", "optimum", "gtl", "racing", "premium",
)

# Kanonik yakıtların tamamı litre (ya da Elektrik için kWh) bazlıdır.
# Kilogram bazlı ürünler (Fuel Oil, Kalorifer Yakıtı/Kalyak) yakıt değildir.
_WEIGHT_UNIT_MARKERS = ("/kg", "tl/kg", "(kg)")


def _normalize_header(value: object) -> str:
    """Başlık metnini karşılaştırma için sadeleştirir (Türkçe -> ASCII, tek boşluk)."""
    return clean_text(value).translate(CITY_REPLACEMENTS).lower()


def _is_weight_priced(header: str) -> bool:
    return any(marker in header for marker in _WEIGHT_UNIT_MARKERS)


def _is_premium(header: str) -> bool:
    return any(marker in header for marker in PREMIUM_MARKERS)


def resolve_fuel_columns(headers: Iterable[object]) -> dict[str, list[int]]:
    """Başlık listesinden {kanonik yakıt: [tercih sırasıyla kolon indeksleri]} üretir.

    Eşleşmeyen ya da kilogram bazlı kolonlar sonuca girmez.
    """
    candidates: dict[str, list[tuple[int, int]]] = {}
    for index, raw_header in enumerate(headers):
        header = _normalize_header(raw_header)
        if not header or _is_weight_priced(header):
            continue
        fuel = normalize_fuel(header)
        if fuel is None:
            continue
        rank = 1 if _is_premium(header) else 0
        candidates.setdefault(fuel, []).append((rank, index))

    resolved: dict[str, list[int]] = {}
    for fuel, entries in candidates.items():
        entries.sort()  # (rank, index) -> standart kolonlar önce, soldan sağa
        resolved[fuel] = [index for _rank, index in entries]
    return resolved


def price_from_columns(
    cols: Sequence[object],
    indices: Iterable[int],
    *,
    parse: Callable[[object], float | None] = first_price_in_cell,
):
    """Verilen kolonları sırayla dener, ilk geçerli fiyatı döner.

    Fallback yalnızca AYNI yakıta ait kolonlar arasında yapılır — bu yüzden
    bir hücrenin boş olması başka bir ürünün fiyatının okunmasına yol açamaz.
    """
    for index in indices:
        if 0 <= index < len(cols):
            price = parse(cols[index])
            if price is not None:
                return price
    return None


def prices_from_row(
    cols: Sequence[object],
    column_map: dict[str, list[int]],
    *,
    fuels: Iterable[str] = ("Kursunsuz 95", "Motorin", "LPG"),
    parse: Callable[[object], float | None] = first_price_in_cell,
) -> dict[str, float]:
    """Tek bir veri satırından kanonik yakıt fiyatlarını çıkarır."""
    prices: dict[str, float] = {}
    for fuel in fuels:
        indices = column_map.get(fuel)
        if not indices:
            continue
        price = price_from_columns(cols, indices, parse=parse)
        if price is not None:
            prices[fuel] = price
    return prices


def describe_column_map(column_map: dict[str, list[int]]) -> str:
    """Log için okunabilir özet — koşu çıktısında hangi kolonun seçildiği görünür."""
    if not column_map:
        return "(eşleşen yakıt kolonu yok)"
    return ", ".join(
        f"{fuel}->{indices}" for fuel, indices in sorted(column_map.items())
    )
