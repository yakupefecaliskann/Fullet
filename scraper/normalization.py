from __future__ import annotations

import re
import unicodedata
from typing import Any

from config import BRAND_ALIASES, CITY_REPLACEMENTS, ISTANBUL_REGION_DISTRICTS, VALID_BRANDS

def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text

def normalize_city(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""
    text = text.translate(CITY_REPLACEMENTS).upper()
    text = text.replace("ISTANBUL ANADOLU", "ISTANBUL")
    text = text.replace("ISTANBUL AVRUPA", "ISTANBUL")
    text = text.replace("(AVRUPA)", "")
    text = text.replace("(ANADOLU)", "")
    text = text.replace("ISTANBUL / ANADOLU", "ISTANBUL")
    text = text.replace("ISTANBUL / AVRUPA", "ISTANBUL")
    text = text.replace("İSTANBUL", "ISTANBUL")
    text = clean_text(text)
    city_aliases = {
        "AFYON": "AFYONKARAHISAR",
        "K.MARAS": "KAHRAMANMARAS",
        "KAHRAMANMARAŞ": "KAHRAMANMARAS",
        "ICEL": "MERSIN",
        "İÇEL": "MERSIN",
    }
    return city_aliases.get(text, text)

# Türkiye'nin 81 ili, normalize edilmiş (ASCII, büyük harf) biçimde.
# shell_bot._split_city bu listeyi buradan alır — eskiden kendi kopyasını
# taşıyordu ve iki liste ayrışabilirdi.
PROVINCES = frozenset({
    "ADANA", "ADIYAMAN", "AFYONKARAHISAR", "AGRI", "AKSARAY", "AMASYA",
    "ANKARA", "ANTALYA", "ARDAHAN", "ARTVIN", "AYDIN", "BALIKESIR",
    "BARTIN", "BATMAN", "BAYBURT", "BILECIK", "BINGOL", "BITLIS",
    "BOLU", "BURDUR", "BURSA", "CANAKKALE", "CANKIRI", "CORUM",
    "DENIZLI", "DIYARBAKIR", "DUZCE", "EDIRNE", "ELAZIG", "ERZINCAN",
    "ERZURUM", "ESKISEHIR", "GAZIANTEP", "GIRESUN", "GUMUSHANE",
    "HAKKARI", "HATAY", "IGDIR", "ISPARTA", "ISTANBUL", "IZMIR",
    "KAHRAMANMARAS", "KARABUK", "KARAMAN", "KARS", "KASTAMONU",
    "KAYSERI", "KILIS", "KIRIKKALE", "KIRKLARELI", "KIRSEHIR",
    "KOCAELI", "KONYA", "KUTAHYA", "MALATYA", "MANISA", "MARDIN",
    "MERSIN", "MUGLA", "MUS", "NEVSEHIR", "NIGDE", "ORDU", "OSMANIYE",
    "RIZE", "SAKARYA", "SAMSUN", "SANLIURFA", "SIIRT", "SINOP",
    "SIRNAK", "SIVAS", "TEKIRDAG", "TOKAT", "TRABZON", "TUNCELI",
    "USAK", "VAN", "YALOVA", "YOZGAT", "ZONGULDAK",
})


def split_province_district(value: Any) -> tuple[str, str]:
    """'MERAM/KONYA' -> ('KONYA', 'MERAM'). İl değilse ('', '') döner.

    İstasyon envanterinde 20 satırın `il` kolonu "İLÇE/İL" birleşik biçimde
    yazılmıştı (`MERAM/KONYA`, `KECIOREN/ANKARA`, ...). `_station_targets`
    fiyat yazarken `.eq("il", "KONYA")` sorguluyor; bu satırlar hiçbir
    sorguya uymadığı için canlı ölçümde **20'sinin de 0 taze fiyatı** vardı.
    Hangi tarafın il olduğu konuma göre değil, 81 il listesine bakılarak
    belirlenir — kaynaklar iki sırayı da kullanıyor.
    """
    text = normalize_city(value)
    if "/" not in text:
        return "", ""
    parts = [part.strip() for part in text.split("/") if part.strip()]
    if len(parts) != 2:
        return "", ""
    left, right = parts
    if right in PROVINCES and left not in PROVINCES:
        return right, left
    if left in PROVINCES and right not in PROVINCES:
        return left, right
    return "", ""


def normalize_province(value: Any) -> str:
    """İl bekleyen alanlar için normalize_city + birleşik değer çözümlemesi."""
    province, _ = split_province_district(value)
    return province or normalize_city(value)


def istanbul_region_from_city(value: Any) -> str:
    text = clean_text(value).translate(CITY_REPLACEMENTS).upper()
    if "ISTANBUL" not in text:
        return ""
    if "ANADOLU" in text:
        return "ANADOLU"
    if "AVRUPA" in text:
        return "AVRUPA"
    return ""

def _station_district_in_istanbul_region(district: Any, region: str) -> bool:
    normalized = normalize_city(district)
    return normalized in ISTANBUL_REGION_DISTRICTS.get(region, set())

def normalize_brand(value: Any, default_brand: str | None = None) -> str | None:
    candidates = [clean_text(value), clean_text(default_brand)]
    for candidate in candidates:
        if not candidate:
            continue
        upper = candidate.translate(CITY_REPLACEMENTS).upper()
        for alias, brand in BRAND_ALIASES.items():
            if upper == alias or upper.startswith(f"{alias} ") or f" {alias} " in f" {upper} ":
                return brand
    return default_brand if default_brand in VALID_BRANDS else None

def normalize_fuel(value: Any) -> str | None:
    # CITY_REPLACEMENTS Türkçe harfleri ASCII'ye indirger (ş->S, ı->I, ...).
    # Bu olmadan "kurşunsuz" metni "kursunsuz" testine takılmıyor ve sınıflama
    # yalnızca sondaki "95" fallback'i sayesinde tesadüfen doğru çalışıyordu —
    # kaynak "95" yazmayı bıraktığında sessizce bozulurdu (yol haritası S1-7).
    text = clean_text(value).translate(CITY_REPLACEMENTS).lower()
    if not text:
        return None
    if "kursunsuz" in text or "benzin" in text or "95" in text:
        return "Kursunsuz 95"
    # "diesel" (İngilizce) şart: Petrol Ofisi "V/Max Diesel", BP "BP Diesel",
    # Shell "Fuelsave Diesel" başlıklarını kullanıyor. Başlık tabanlı kolon
    # eşlemesi (column_mapping.py) bu kelimeyi tanımazsa motorin kolonu
    # bulunamaz.
    if (
        "motorin" in text
        or "dizel" in text
        or "diesel" in text
        or "mazot" in text
    ):
        return "Motorin"
    if "lpg" in text or "oto gaz" in text or "otogaz" in text:
        return "LPG"
    if (
        "elektrik" in text
        or "sarj" in text
        or "kwh" in text
        or text == "ev"
    ):
        return "Elektrik"
    return None

def parse_price(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        price = float(value)
        return round(price, 2) if 0 < price < 300 else None

    text = clean_text(value)
    if not text or text == "-":
        return None
    text = re.sub(r"[^0-9,.\-]", "", text)
    if not text or text == "-":
        return None

    has_comma = "," in text
    has_dot = "." in text
    if has_comma and has_dot:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif has_comma:
        text = text.replace(",", ".")

    try:
        price = float(text)
    except ValueError:
        return None
    return round(price, 2) if 0 < price < 300 else None

def parse_coordinate(value: Any, *, latitude: bool) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        coord = float(value)
    else:
        text = clean_text(value)
        if not text or text == "-":
            return None
        text = re.sub(r"[^0-9,.\-]", "", text)
        if not text or text == "-":
            return None

        has_comma = "," in text
        has_dot = "." in text
        if has_comma and has_dot:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif has_comma:
            text = text.replace(",", ".")

        try:
            coord = float(text)
        except ValueError:
            return None

    if latitude and 35 <= coord <= 43:
        return round(coord, 6)
    if not latitude and 25 <= coord <= 46:
        return round(coord, 6)
    return None
