"""Pricing normalization and meter matching.

User Story 5 (T051): Provide simple, explainable matching rules to map a
requested usage line to an Azure Retail Prices API item.

This module intentionally uses best-effort matching; callers should record
pricing gaps when no match is found.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class PricingMatchRequest:
    service_name: str
    arm_region_name: str
    sku_name: Optional[str] = None
    product_name_contains: Optional[str] = None
    meter_name_contains: Optional[str] = None


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _contains(haystack: str, needle: Optional[str]) -> bool:
    if not needle:
        return True
    return _norm(needle) in _norm(haystack)


def find_best_retail_price_item(
    items: Iterable[Dict[str, Any]],
    request: PricingMatchRequest,
) -> Optional[Dict[str, Any]]:
    """Return the first best-effort match for a request.

    Matching order:
    1) serviceName + armRegionName + skuName (exact-ish)
    2) serviceName + armRegionName + product/meter contains
    """
    candidates: List[Dict[str, Any]] = []

    for item in items:
        service = _norm(item.get("serviceName"))
        region = _norm(item.get("armRegionName"))
        if service != _norm(request.service_name):
            continue
        if region != _norm(request.arm_region_name):
            continue
        candidates.append(item)

    if not candidates:
        return None

    if request.sku_name:
        sku_req = _norm(request.sku_name)
        for item in candidates:
            if _norm(item.get("armSkuName")) == sku_req or _norm(item.get("skuName")) == sku_req:
                return item

    for item in candidates:
        if not _contains(str(item.get("productName") or ""), request.product_name_contains):
            continue
        if not _contains(str(item.get("meterName") or ""), request.meter_name_contains):
            continue
        return item

    return candidates[0]


def extract_unit_price(item: Dict[str, Any]) -> Optional[float]:
    value = item.get("retailPrice")
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return None


def extract_currency(item: Dict[str, Any]) -> Optional[str]:
    currency = item.get("currencyCode")
    cur = str(currency or "").strip()
    return cur or None
