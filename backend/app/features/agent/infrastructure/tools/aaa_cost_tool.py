"""AAA cost estimation tool.

Provides a dedicated pricing tool that computes baseline cost estimates using
the Azure Retail Prices API and records `costEstimates` into ProjectState.
IaC persistence is intentionally excluded to keep responsibilities decoupled.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.shared.pricing.pricing_normalizer import (
    PricingMatchRequest,
    extract_currency,
    extract_unit_price,
    find_best_retail_price_item,
)
from app.shared.pricing.retail_prices_client import AzureRetailPricesClient

_MIN_SEARCH_TERM_LENGTH = 3
_MAX_DISCOVERED_ITEMS = 300
_MAX_SEARCH_TERMS = 8
_MIN_RELAXED_MATCH_SCORE = 3
_RELAXED_MATCH_FIELDS = ("productName", "serviceName", "meterName")


@dataclass(frozen=True)
class _RelaxedMatchCriteria:
    target_region: str
    sku_name: str
    product_name_contains: str
    meter_name_contains: str
    service_name: str
    terms: tuple[str, ...]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_pricing_log(*, entries: list[dict[str, Any]]) -> str:
    payload = {
        "tool": "azure_retail_prices",
        "executedAt": _now_iso(),
        "entries": entries,
    }
    return "AAA_PRICING_LOG\n```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```\n"


class PricingLineItemInput(BaseModel):
    """A requested usage line for baseline pricing."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    name: str = Field(min_length=1, description="Display name for this line")
    service_name: str = Field(min_length=1, description="Retail Prices serviceName")
    arm_region_name: str = Field(min_length=1, description="Retail Prices armRegionName (e.g., eastus)")

    sku_name: str | None = Field(default=None, description="sku_name or arm_sku_name")
    product_name_contains: str | None = Field(default=None, description="Substring match for product_name")
    meter_name_contains: str | None = Field(default=None, description="Substring match for meter_name")

    monthly_quantity: float = Field(gt=0, description="Monthly quantity in the meter's unit")


class AAAGenerateCostInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel, extra="forbid")

    pricing_lines: list[PricingLineItemInput] = Field(
        default_factory=list,
        description="Requested pricing lines for baseline monthly cost calculation",
    )
    pricing_catalog: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional Retail Prices Items[] payload to avoid external calls (tests/offline)",
    )
    baseline_reference_total_monthly_cost: float | None = Field(
        default=None,
        description="Optional baseline reference total to compute variance% against",
    )


class AAAGenerateCostToolInput(BaseModel):
    payload: str | dict[str, Any] = Field(
        description="A JSON object (or JSON string) matching AAAGenerateCostInput."
    )


class AAAGenerateCostTool(BaseTool):
    name: str = "aaa_record_cost_estimate"
    description: str = (
        "Compute and record baseline cost estimates using Azure Retail Prices API. "
        "Returns an AAA_STATE_UPDATE JSON block with costEstimates."
    )

    args_schema: type[BaseModel] = AAAGenerateCostToolInput

    def _run(
        self,
        payload: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            raw_data = self._parse_payload(payload, **kwargs)
            args = AAAGenerateCostInput.model_validate(raw_data)
            if args.pricing_lines and args.pricing_catalog is None:
                raise ValueError(
                    "pricingLines requires async execution (external pricing API). "
                    "Use async tool call or provide pricingCatalog."
                )

            updates = self._build_updates(args, catalog_items=args.pricing_catalog)
            return self._format_response(updates, args)
        except Exception as exc:  # noqa: BLE001
            return f"ERROR: {exc!s}"

    async def _arun(self, payload: str | dict[str, Any] | None = None, **kwargs: Any) -> str:
        try:
            raw_data = self._parse_payload(payload, **kwargs)
            args = AAAGenerateCostInput.model_validate(raw_data)

            pricing_items = args.pricing_catalog
            pricing_log_entries: list[dict[str, Any]] = []
            if args.pricing_lines and pricing_items is None:
                pricing_items, pricing_log_entries = await self._fetch_live_prices(
                    args.pricing_lines
                )

            updates = self._build_updates(args, catalog_items=pricing_items)
            return self._format_response(updates, args, pricing_log_entries=pricing_log_entries)
        except Exception as exc:  # noqa: BLE001
            return f"ERROR: {exc!s}"

    def _parse_payload(self, payload: str | dict[str, Any] | None, **kwargs: Any) -> Any:
        if payload is None:
            payload = kwargs.get("payload") or kwargs.get("tool_input")
            if payload is None:
                payload = kwargs
            if not payload:
                raise ValueError(f"Missing payload for {self.name}")

        if isinstance(payload, str):
            try:
                return json.loads(payload.strip())
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid JSON payload for cost estimation.") from exc
        return payload

    def _build_updates(
        self,
        args: AAAGenerateCostInput,
        catalog_items: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        if args.pricing_lines and catalog_items is not None:
            cost_estimate = _compute_cost_estimate(
                pricing_lines=args.pricing_lines,
                catalog_items=catalog_items,
                baseline_reference_total=args.baseline_reference_total_monthly_cost,
            )
            updates["costEstimates"] = [cost_estimate]
        return updates

    def _format_response(
        self,
        updates: dict[str, Any],
        args: AAAGenerateCostInput,
        *,
        pricing_log_entries: list[dict[str, Any]] | None = None,
    ) -> str:
        payload_json = json.dumps(updates, ensure_ascii=False, indent=2)
        output = (
            f"Recorded cost estimate at {_now_iso()} (pricingLines={len(args.pricing_lines)}).\n"
            "\n"
            "AAA_STATE_UPDATE\n"
            "```json\n"
            f"{payload_json}\n"
            "```"
        )

        if pricing_log_entries:
            output += _append_pricing_log(entries=pricing_log_entries)

        return output

    async def _fetch_live_prices(
        self, pricing_lines: list[PricingLineItemInput]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        client = AzureRetailPricesClient()
        items: list[dict[str, Any]] = []
        log_entries: list[dict[str, Any]] = []

        for line in pricing_lines:
            region = line.arm_region_name.replace("'", "''")
            if not region:
                continue

            attempts: list[dict[str, Any]] = []
            selected_items: list[dict[str, Any]] = []

            strict_service = line.service_name.replace("'", "''")
            strict_filter = f"serviceName eq '{strict_service}' and armRegionName eq '{region}'"
            strict_items, strict_meta = await client.query_all_with_meta(
                filter_expr=strict_filter,
                max_pages=3,
            )
            attempts.append(
                {
                    "mode": "strict_service_region",
                    "filterExpr": strict_filter,
                    "matchedItems": len(strict_items),
                    "meta": strict_meta,
                }
            )
            selected_items = strict_items

            if not selected_items:
                discovered_items, discovered_attempts = await _discover_items_for_line(
                    client=client,
                    line=line,
                    region=region,
                )
                attempts.extend(discovered_attempts)
                selected_items = discovered_items

            items = _merge_unique_items(items, selected_items)

            log_entries.append(
                {
                    "name": line.name,
                    "requestedServiceName": line.service_name,
                    "armRegionName": line.arm_region_name,
                    "matchedItems": len(selected_items),
                    "attempts": attempts,
                }
            )

        return items, log_entries


def _build_match_requests(line: PricingLineItemInput) -> list[PricingMatchRequest]:
    return [
        PricingMatchRequest(
            service_name=line.service_name,
            arm_region_name=line.arm_region_name,
            sku_name=line.sku_name,
            product_name_contains=line.product_name_contains,
            meter_name_contains=line.meter_name_contains,
        )
    ]


def _extract_search_terms(line: PricingLineItemInput) -> list[str]:
    seeds = [
        line.sku_name or "",
        line.product_name_contains or "",
        line.meter_name_contains or "",
        line.service_name or "",
        line.name or "",
    ]
    stop_words = {
        "azure",
        "baseline",
        "service",
        "services",
        "monthly",
        "cost",
        "estimate",
    }
    terms: list[str] = []
    seen: set[str] = set()
    for seed in seeds:
        text = seed.strip()
        if not text:
            continue
        if len(text) >= _MIN_SEARCH_TERM_LENGTH:
            key = text.lower()
            if key not in seen:
                seen.add(key)
                terms.append(text)
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]{1,}", text):
            key = token.lower()
            if len(key) < _MIN_SEARCH_TERM_LENGTH or key in stop_words:
                continue
            if key in seen:
                continue
            seen.add(key)
            terms.append(token)
    return terms[:_MAX_SEARCH_TERMS]


def _merge_unique_items(
    base: list[dict[str, Any]],
    extra: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    merged: list[dict[str, Any]] = []
    for item in [*base, *extra]:
        key = (
            item.get("serviceName"),
            item.get("armRegionName"),
            item.get("productName"),
            item.get("meterName"),
            item.get("armSkuName"),
            item.get("skuName"),
            item.get("retailPrice"),
            item.get("unitOfMeasure"),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


async def _discover_items_for_line(
    *,
    client: AzureRetailPricesClient,
    line: PricingLineItemInput,
    region: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    terms = _extract_search_terms(line)
    attempts: list[dict[str, Any]] = []
    discovered: list[dict[str, Any]] = []

    for term in terms:
        if len(discovered) >= _MAX_DISCOVERED_ITEMS:
            break
        safe_term = term.replace("'", "''")
        for field in _RELAXED_MATCH_FIELDS:
            filter_expr = f"armRegionName eq '{region}' and contains({field}, '{safe_term}')"
            line_items, meta = await client.query_all_with_meta(
                filter_expr=filter_expr,
                max_pages=2,
            )
            attempts.append(
                {
                    "mode": "discovery_contains",
                    "field": field,
                    "term": term,
                    "filterExpr": filter_expr,
                    "matchedItems": len(line_items),
                    "meta": meta,
                }
            )
            discovered = _merge_unique_items(discovered, line_items)
            if len(discovered) >= _MAX_DISCOVERED_ITEMS:
                break

    return discovered, attempts


def _normalize_match_value(value: str | None) -> str:
    return value.strip().lower() if value else ""


def _build_relaxed_match_criteria(line: PricingLineItemInput) -> _RelaxedMatchCriteria:
    return _RelaxedMatchCriteria(
        target_region=_normalize_match_value(line.arm_region_name),
        sku_name=_normalize_match_value(line.sku_name),
        product_name_contains=_normalize_match_value(line.product_name_contains),
        meter_name_contains=_normalize_match_value(line.meter_name_contains),
        service_name=_normalize_match_value(line.service_name),
        terms=tuple(_normalize_match_value(term) for term in _extract_search_terms(line)),
    )


def _score_catalog_item(
    *,
    item: dict[str, Any],
    criteria: _RelaxedMatchCriteria,
) -> tuple[int, float] | None:
    if _normalize_match_value(str(item.get("armRegionName") or "")) != criteria.target_region:
        return None

    unit_price = extract_unit_price(item)
    if unit_price is None or unit_price <= 0:
        return None

    service = _normalize_match_value(str(item.get("serviceName") or ""))
    product = _normalize_match_value(str(item.get("productName") or ""))
    meter = _normalize_match_value(str(item.get("meterName") or ""))
    sku = _normalize_match_value(str(item.get("armSkuName") or item.get("skuName") or ""))
    item_type = _normalize_match_value(str(item.get("type") or ""))

    score = 0
    if criteria.sku_name and criteria.sku_name == sku:
        score += 15
    if criteria.product_name_contains and criteria.product_name_contains in product:
        score += 8
    if criteria.meter_name_contains and criteria.meter_name_contains in meter:
        score += 6
    if criteria.service_name and criteria.service_name in service:
        score += 5

    for term in criteria.terms:
        if term and (term in service or term in product or term in meter or term in sku):
            score += 1

    if item_type == "consumption":
        score += 2

    return score, unit_price


def _find_relaxed_match(
    *,
    line: PricingLineItemInput,
    catalog_items: list[dict[str, Any]],
) -> dict[str, Any] | None:
    criteria = _build_relaxed_match_criteria(line)

    best_item: dict[str, Any] | None = None
    best_score = -1
    best_price = float("inf")

    for item in catalog_items:
        scored = _score_catalog_item(item=item, criteria=criteria)
        if scored is None:
            continue
        score, unit_price = scored

        if score > best_score or (score == best_score and unit_price < best_price):
            best_item = item
            best_score = score
            best_price = unit_price

    if best_score < _MIN_RELAXED_MATCH_SCORE:
        return None
    return best_item


def _compute_cost_estimate(
    *,
    pricing_lines: list[PricingLineItemInput],
    catalog_items: list[dict[str, Any]],
    baseline_reference_total: float | None,
) -> dict[str, Any]:
    estimate_id = str(uuid.uuid4())
    currency: str | None = None

    line_items: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    total = 0.0

    for line in pricing_lines:
        if line.monthly_quantity <= 0:
            continue

        match: dict[str, Any] | None = None
        for request in _build_match_requests(line):
            match = find_best_retail_price_item(catalog_items, request)
            if match is not None:
                break

        if match is None:
            match = _find_relaxed_match(line=line, catalog_items=catalog_items)

        if match is None:
            gaps.append({"name": line.name, "reason": "no_match", "request": line.model_dump()})
            continue

        unit_price = extract_unit_price(match)
        if unit_price is None:
            gaps.append(
                {"name": line.name, "reason": "missing_unit_price", "request": line.model_dump()}
            )
            continue

        currency = currency or extract_currency(match)
        monthly_cost = unit_price * line.monthly_quantity
        total += monthly_cost

        line_items.append(
            {
                "id": str(uuid.uuid4()),
                "name": line.name,
                "serviceName": match.get("serviceName"),
                "productName": match.get("productName"),
                "meterName": match.get("meterName"),
                "skuName": match.get("armSkuName") or match.get("skuName"),
                "unitOfMeasure": match.get("unitOfMeasure"),
                "unitPrice": unit_price,
                "monthlyQuantity": line.monthly_quantity,
                "monthlyCost": monthly_cost,
            }
        )

    variance_pct = None
    if baseline_reference_total is not None and baseline_reference_total > 0:
        variance_pct = ((total - baseline_reference_total) / baseline_reference_total) * 100.0

    return {
        "id": estimate_id,
        "createdAt": _now_iso(),
        "currencyCode": currency or "USD",
        "totalMonthlyCost": total,
        "lineItems": line_items,
        "pricingGaps": gaps,
        "baselineReferenceTotalMonthlyCost": baseline_reference_total,
        "variancePct": variance_pct,
    }


def create_cost_tools() -> list[BaseTool]:
    return [AAAGenerateCostTool()]
