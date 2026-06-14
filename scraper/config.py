from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import Client, create_client

SCRAPER_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRAPER_DIR.parent

load_dotenv(SCRAPER_DIR / ".env")
load_dotenv(PROJECT_DIR / ".env")

CANONICAL_FUELS = ("Kursunsuz 95", "Motorin", "LPG", "Elektrik")
VALID_BRANDS = {
    "Shell",
    "Opet",
    "Petrol Ofisi",
    "BP",
    "Aytemiz",
    "TotalEnergies",
    "Türkiye Petrolleri",
}

OFFICIAL_REGIONAL_SOURCES = {
    "api.opet.com.tr/api/fuelprices/allprices",
    "petrolofisi.com.tr/akaryakit-fiyatlari",
    "petrolofisi.com.tr/akaryakit-fiyatlari-bp",
    "aytemiz.com.tr/akaryakit-fiyatlari",
    "turkiyeshell.com/pompatest/History.aspx",
    "apimobile.guzelenerji.com.tr/exapi/fuel_prices",
    "www.tppd.com.tr/akaryakit-fiyatlari",
}

OFFICIAL_STATION_SOURCES = {
    "apimobile.guzelenerji.com.tr/exapi/stations",
    "www.tppd.com.tr/tr/stationmaplist",
    "find.shell.com/tr/fuel",
}

BRAND_ALIASES = {
    "SHELL": "Shell",
    "OPET": "Opet",
    "PETROL OFISI": "Petrol Ofisi",
    "PETROL OFİSİ": "Petrol Ofisi",
    "PO": "Petrol Ofisi",
    "BP": "BP",
    "TOTAL": "TotalEnergies",
    "TOTALENERGIES": "TotalEnergies",
    "TOTAL ENERGIES": "TotalEnergies",
    "AYTEMIZ": "Aytemiz",
    "AYTEMİZ": "Aytemiz",
    "TP": "Türkiye Petrolleri",
    "TPPD": "Türkiye Petrolleri",
    "TURKIYE PETROLLERI": "Türkiye Petrolleri",
    "TÜRKİYE PETROLLERİ": "Türkiye Petrolleri",
    "TURKIYE PETROL": "Türkiye Petrolleri",
}

CITY_REPLACEMENTS = str.maketrans({
    "İ": "I", "I": "I", "ı": "I", "Ş": "S", "ş": "S",
    "Ç": "C", "ç": "C", "Ğ": "G", "ğ": "G", "Ü": "U",
    "ü": "U", "Ö": "O", "ö": "O",
})

ISTANBUL_REGION_DISTRICTS = {
    "ANADOLU": {
        "ADALAR", "ATASEHIR", "BEYKOZ", "CEKMEKOY", "KADIKOY", "KARTAL", 
        "MALTEPE", "PENDIK", "SANCAKTEPE", "SILE", "SULTANBEYLI", "TUZLA", 
        "UMRANIYE", "USKUDAR",
    },
    "AVRUPA": {
        "ARNAVUTKOY", "AVCILAR", "BAGCILAR", "BAHCELIEVLER", "BAKIRKOY", 
        "BASAKSEHIR", "BAYRAMPASA", "BESIKTAS", "BEYLIKDUZU", "BEYOGLU", 
        "BUYUKCEKMECE", "CATALCA", "ESENLER", "ESENYURT", "EYUP", "EYUPSULTAN", 
        "FATIH", "GAZIOSMANPASA", "GUNGOREN", "KAGITHANE", "KUCUKCEKMECE", 
        "SARIYER", "SILIVRI", "SULTANGAZI", "SISLI", "ZEYTINBURNU",
    },
}

def _get_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None

SUPABASE_URL = _get_env("SUPABASE_URL")
SUPABASE_KEY = _get_env("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY", "SUPABASE_KEY")

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as exc:
        print(f"[WARN] Supabase client could not be created: {exc}")

def is_dry_run() -> bool:
    return os.environ.get("FULLET_DRY_RUN", "0") == "1"

def is_write_allowed() -> bool:
    return os.environ.get("FULLET_ALLOW_DB_WRITE", "0") == "1"

def allow_inferred_data() -> bool:
    return os.environ.get("FULLET_ALLOW_INFERRED_DATA", "0") == "1"
