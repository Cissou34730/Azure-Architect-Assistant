"""Pricing normalization and meter matching.

User Story 5 (T051): Provide simple, explainable matching rules to map a
requested usage line to an Azure Retail Prices API item.

This module intentionally uses best-effort matching; callers should record
pricing gaps when no match is found.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PricingMatchRequest:
    service_name: str
    arm_region_name: str
    sku_name: str | None = None
    product_name_contains: str | None = None
    meter_name_contains: str | None = None


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _contains(haystack: str, needle: str | None) -> bool:
    if not needle:
        return True
    return _norm(needle) in _norm(haystack)


def _filter_by_service_and_region(
    items: Iterable[dict[str, Any]], request: PricingMatchRequest
) -> list[dict[str, Any]]:
    """Filter candidates by service and region."""
    candidates: list[dict[str, Any]] = []
    target_service = _norm(request.service_name)
    target_region = _norm(request.arm_region_name)
    for item in items:
        service = _norm(item.get("serviceName"))
        region = _norm(item.get("armRegionName"))
        if service == target_service and region == target_region:
            candidates.append(item)
    return candidates


def _find_by_sku(candidates: list[dict[str, Any]], sku_name: str | None) -> dict[str, Any] | None:
    """Find candidate with matching SKU name."""
    if not sku_name:
        return None
    sku_req = _norm(sku_name)
    for item in candidates:
        if _norm(item.get("armSkuName")) == sku_req or _norm(item.get("skuName")) == sku_req:
            return item
    return None


def _find_by_contains(
    candidates: list[dict[str, Any]], request: PricingMatchRequest
) -> dict[str, Any] | None:
    """Find candidate by product/meter name contents."""
    for item in candidates:
        if not _contains(str(item.get("productName") or ""), request.product_name_contains):
            continue
        if not _contains(str(item.get("meterName") or ""), request.meter_name_contains):
            continue
        return item
    return None


def find_best_retail_price_item(
    items: Iterable[dict[str, Any]],
    request: PricingMatchRequest,
) -> dict[str, Any] | None:
    """Return the first best-effort match for a request.

    Matching order:
    1) serviceName + armRegionName + skuName (exact-ish)
    2) serviceName + armRegionName + product/meter contains
    """
    candidates = _filter_by_service_and_region(items, request)
    if not candidates:
        return None

    # 1) Exact SKU Match
    sku_match = _find_by_sku(candidates, request.sku_name)
    if sku_match:
        return sku_match

    # 2) Contains Match
    contains_match = _find_by_contains(candidates, request)
    if contains_match:
        return contains_match

    return candidates[0]



def extract_unit_price(item: dict[str, Any]) -> float | None:
    value = item.get("retailPrice")
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return None


def extract_currency(item: dict[str, Any]) -> str | None:
    currency = item.get("currencyCode")
    cur = str(currency or "").strip()
    return cur or None

