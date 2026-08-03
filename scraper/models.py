from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PriceRow:
    fuel_type: str
    price: float
    status: str = "fresh"  # fresh, stale, unknown

@dataclass
class Station:
    brand: str
    name: str
    city: str
    district: str
    latitude: Optional[float]
    longitude: Optional[float]
    source: str
    prices: dict[str, PriceRow] = field(default_factory=dict)
    address: Optional[str] = None
    is_official_regional: bool = False
    visibility_status: str = "visible" # visible, low_priority, hidden
    price_status: str = "fresh" # fresh, stale, unknown

@dataclass(frozen=True)
class SaveSummary:
    stations_touched: int = 0
    prices_touched: int = 0
    skipped_items: int = 0
    brands: tuple[str, ...] = ()
