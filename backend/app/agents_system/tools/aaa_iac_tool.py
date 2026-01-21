"""AAA IaC + cost tool.

User Story 5 (T033/T034): Provide a tool to persist IaC artifacts and their
static validation results (recording only).

User Story 5 (T050-T053): Optionally compute a baseline monthly cost using the
Azure Retail Prices API, record pricing gaps, and compute variance vs an
optional baseline reference.

This tool is designed for the agent system:
- It returns an AAA_STATE_UPDATE JSON block
- It is append-only and safe with the no-overwrite merge rules

For deterministic/offline runs (and for unit tests), callers can provide
`pricingCatalog` to avoid calling the external pricing API.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from langchain.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from ...services.pricing.pricing_normalizer import (
    PricingMatchRequest,
    extract_currency,
    extract_unit_price,
    find_best_retail_price_item,
)
from ...services.pricing.retail_prices_client import AzureRetailPricesClient


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


IacFormat = Literal["bicep", "terraform", "arm", "yaml", "json", "other"]
ValidationStatus = Literal["pass", "fail", "skipped"]


class IaCFileInput(BaseModel):
    path: str = Field(min_length=1, description="Relative path for the file (e.g., infra/main.bicep)")
    format: IacFormat = Field(description="IaC format")
    content: str = Field(min_length=1, description="File content")


class IaCValidationResultInput(BaseModel):
    tool: str = Field(min_length=1, description="Validator name (e.g., bicep build, terraform validate)")
    status: ValidationStatus = Field(description="pass|fail|skipped")
    output: str | None = Field(default=None, description="Raw output (trimmed) or summary")


class PricingLineItemInput(BaseModel):
    """A requested usage line for baseline pricing."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    name: str = Field(min_length=1, description="Display name for this line")
    service_name: str = Field(min_length=1, description="Retail Prices serviceName")
    arm_region_name: str = Field(min_length=1, description="Retail Prices armRegionName (e.g., westeurope)")

    sku_name: str | None = Field(default=None, description="sku_name or arm_sku_name")
    product_name_contains: str | None = Field(default=None, description="Substring match for product_name")
    meter_name_contains: str | None = Field(default=None, description="Substring match for meter_name")

    monthly_quantity: float = Field(gt=0, description="Monthly quantity in the meter's unit")


class AAAGenerateIacAndCostInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    iac_files: list[IaCFileInput] = Field(default_factory=list, description="IaC files to persist")
    validation_results: list[IaCValidationResultInput] = Field(
        default_factory=list, description="Static validation results (recording only)"
    )

    # Cost estimation (optional)
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


class AAAGenerateIacToolInput(BaseModel):
    """Raw tool payload for IaC and cost."""

    payload: str | dict[str, Any] = Field(
        description="A JSON object (or JSON string) matching AAAGenerateIacAndCostInput."
    )


class AAAGenerateIacTool(BaseTool):
    name: str = "aaa_record_iac_and_cost"
    description: str = (
        "Record IaC artifacts, static validation results, and optionally compute baseline monthly cost "
        "from Azure Retail Prices API. Returns an AAA_STATE_UPDATE JSON block."
        "For deterministic runs, provide pricingCatalog to avoid calling the external pricing API."
    )

    args_schema: type[BaseModel] = AAAGenerateIacToolInput

    def _run(
        self,
        payload: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """Synchronous record for IaC and cost (requires offline pricing catalog)."""
        try:
            raw_data = self._parse_payload(payload, **kwargs)
            args = AAAGenerateIacAndCostInput.model_validate(raw_data)

            if args.pricing_lines and args.pricing_catalog is None:
                raise ValueError(
                    "pricingLines requires async execution (external pricing API). Use async tool call or provide pricingCatalog."
                )

            updates = self._build_updates(args, catalog_items=args.pricing_catalog)
            return self._format_response(updates, args)
        except Exception as exc:  # noqa: BLE001
            return f"ERROR: {exc!s}"

    async def _arun(self, payload: str | dict[str, Any] | None = None, **kwargs: Any) -> str:
        """Asynchronous execution that can fetch live Azure prices."""
        try:
            raw_data = self._parse_payload(payload, **kwargs)
            args = AAAGenerateIacAndCostInput.model_validate(raw_data)

            pricing_items = args.pricing_catalog
            if args.pricing_lines and pricing_items is None:
                pricing_items = await self._fetch_live_prices(args.pricing_lines)

            updates = self._build_updates(args, catalog_items=pricing_items)
            return self._format_response(updates, args)
        except Exception as exc:  # noqa: BLE001
            return f"ERROR: {exc!s}"

    def _parse_payload(self, payload: str | dict[str, Any] | None, **kwargs: Any) -> Any:
        """Extract and parse payload from input."""
        if payload is None:
            payload = kwargs.get("payload") or kwargs.get("tool_input") or kwargs
            if not payload:
                raise ValueError("Missing payload for aaa_record_iac_and_cost")

        if isinstance(payload, str):
            try:
                return json.loads(payload.strip())
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid JSON payload for IaC and cost.") from exc
        return payload

    def _build_updates(
        self,
        args: AAAGenerateIacAndCostInput,
        catalog_items: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """Construct the state update dictionary."""
        updates: dict[str, Any] = {}

        iac_files_list = [f.model_dump() for f in args.iac_files]
        val_results_list = [r.model_dump() for r in args.validation_results]

        if iac_files_list or val_results_list:
            updates["iacArtifacts"] = [
                {
                    "id": str(uuid.uuid4()),
                    "createdAt": _now_iso(),
                    "files": iac_files_list,
                    "validationResults": val_results_list,
                }
            ]

        if args.pricing_lines and catalog_items is not None:
            cost_estimate = _compute_cost_estimate(
                pricing_lines=args.pricing_lines,
                catalog_items=catalog_items,
                baseline_reference_total=args.baseline_reference_total_monthly_cost,
            )
            updates["costEstimates"] = [cost_estimate]

        return updates

    def _format_response(self, updates: dict[str, Any], args: AAAGenerateIacAndCostInput) -> str:
        """Format the final tool output with state update block."""
        payload_json = json.dumps(updates, ensure_ascii=False, indent=2)
        return (
            f"Recorded IaC/cost artifacts at {_now_iso()} (iacFiles={len(args.iac_files)}, pricingLines={len(args.pricing_lines)}).\n"
            "\n"
            "AAA_STATE_UPDATE\n"
            "```json\n"
            f"{payload_json}\n"
            "```"
        )

    async def _fetch_live_prices(
        self, pricing_lines: list[PricingLineItemInput]
    ) -> list[dict[str, Any]]:
        """Fetch matching prices for all lines from Azure Retail Prices API."""
        client = AzureRetailPricesClient()
        items: list[dict[str, Any]] = []
        for line in pricing_lines:
            service = line.service_name.replace("'", "''")
            region = line.arm_region_name.replace("'", "''")
            if not service or not region:
                continue
            filter_expr = f"serviceName eq '{service}' and armRegionName eq '{region}'"
            line_items = await client.query_all(filter_expr=filter_expr)
            items.extend(line_items)
        return items


def _compute_cost_estimate(
    *,
    pricing_lines: list[PricingLineItemInput],
    catalog_items: list[dict[str, Any]],
    baseline_reference_total: float | None,
) -> dict[str, Any]:
    """Calculate total cost and per-line breakdown."""
    estimate_id = str(uuid.uuid4())
    currency: str | None = None

    line_items: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    total = 0.0

    for line in pricing_lines:
        if line.monthly_quantity <= 0:
            continue

        request = PricingMatchRequest(
            service_name=line.service_name,
            arm_region_name=line.arm_region_name,
            sku_name=line.sku_name,
            product_name_contains=line.product_name_contains,
            meter_name_contains=line.meter_name_contains,
        )

        match = find_best_retail_price_item(catalog_items, request)
        if not match:
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
            _build_line_item_result(line.name, line.monthly_quantity, monthly_cost, unit_price, match)
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


def _build_line_item_result(
    name: str,
    qty: float,
    cost: float,
    unit_price: float,
    match: dict[str, Any],
) -> dict[str, Any]:
    """Create a single line item result dictionary."""
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "serviceName": match.get("serviceName"),
        "productName": match.get("productName"),
        "meterName": match.get("meterName"),
        "skuName": match.get("armSkuName") or match.get("skuName"),
        "unitOfMeasure": match.get("unitOfMeasure"),
        "unitPrice": unit_price,
        "monthlyQuantity": qty,
        "monthlyCost": cost,
    }


def create_iac_tools() -> list[BaseTool]:
    return [AAAGenerateIacTool()]
