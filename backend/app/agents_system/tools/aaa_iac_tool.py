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
from typing import Any, Dict, List, Literal, Optional, Type, Union

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

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
    output: Optional[str] = Field(default=None, description="Raw output (trimmed) or summary")


class PricingLineItemInput(BaseModel):
    """A requested usage line for baseline pricing."""

    name: str = Field(min_length=1, description="Display name for this line")
    serviceName: str = Field(min_length=1, description="Retail Prices serviceName")
    armRegionName: str = Field(min_length=1, description="Retail Prices armRegionName (e.g., westeurope)")

    skuName: Optional[str] = Field(default=None, description="skuName or armSkuName")
    productNameContains: Optional[str] = Field(default=None, description="Substring match for productName")
    meterNameContains: Optional[str] = Field(default=None, description="Substring match for meterName")

    monthlyQuantity: float = Field(gt=0, description="Monthly quantity in the meter's unit")


class AAAGenerateIacAndCostInput(BaseModel):
    iacFiles: List[IaCFileInput] = Field(default_factory=list, description="IaC files to persist")
    validationResults: List[IaCValidationResultInput] = Field(
        default_factory=list, description="Static validation results (recording only)"
    )

    # Cost estimation (optional)
    pricingLines: List[PricingLineItemInput] = Field(
        default_factory=list,
        description="Requested pricing lines for baseline monthly cost calculation",
    )
    pricingCatalog: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional Retail Prices Items[] payload to avoid external calls (tests/offline)",
    )

    baselineReferenceTotalMonthlyCost: Optional[float] = Field(
        default=None,
        description="Optional baseline reference total to compute variance% against",
    )


class AAAGenerateIacToolInput(BaseModel):
    """Raw tool payload for IaC and cost."""

    payload: Union[str, Dict[str, Any]] = Field(
        description="A JSON object (or JSON string) matching AAAGenerateIacAndCostInput."
    )


class AAAGenerateIacTool(BaseTool):
    name: str = "aaa_record_iac_and_cost"
    description: str = (
        "Record IaC artifacts, static validation results, and optionally compute baseline monthly cost "
        "from Azure Retail Prices API. Returns an AAA_STATE_UPDATE JSON block." 
        "For deterministic runs, provide pricingCatalog to avoid calling the external pricing API."
    )

    args_schema: Type[BaseModel] = AAAGenerateIacToolInput

    def _run(
        self,
        payload: Union[str, Dict[str, Any], None] = None,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        # Accept positional dict payload for compat as well
        if payload is None and args:
            first = args[0]
            if isinstance(first, dict):
                payload = first

        if payload is None:
            # Accept direct keyword args for backwards compatibility with tests
            if "payload" in kwargs:
                payload = kwargs["payload"]
            elif kwargs:
                payload = kwargs
            else:
                raise ValueError("Missing payload for aaa_record_iac_and_cost")

        if isinstance(payload, str):
            try:
                data = json.loads(payload.strip())
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid JSON payload for IaC and cost.") from exc
        else:
            data = payload

        try:
            args = AAAGenerateIacAndCostInput.model_validate(data)
        except Exception as exc:
            return f"ERROR: Validation failed for AAAGenerateIacAndCostInput: {str(exc)}"

        iacFiles = args.iacFiles
        validationResults = args.validationResults
        pricingLines = args.pricingLines
        pricingCatalog = args.pricingCatalog
        baselineReferenceTotalMonthlyCost = args.baselineReferenceTotalMonthlyCost

        iac_artifact_id = str(uuid.uuid4())
        iac_files_list = [f.model_dump() if hasattr(f, "model_dump") else f for f in iacFiles or []]
        val_results_list = [r.model_dump() if hasattr(r, "model_dump") else r for r in validationResults or []]
        pricing_lines_list = [l.model_dump() if hasattr(l, "model_dump") else l for l in pricingLines or []]

        iac_artifact: Dict[str, Any] = {
            "id": iac_artifact_id,
            "createdAt": _now_iso(),
            "files": iac_files_list,
            "validationResults": val_results_list,
        }

        updates: Dict[str, Any] = {}

        if iac_files_list or val_results_list:
            updates["iacArtifacts"] = [iac_artifact]

        cost_estimate = None
        if pricing_lines_list:
            # Compute baseline cost using either provided catalog or live API
            items = pricingCatalog
            if items is None:
                # Live call is async; defer to _arun for production usage.
                raise ValueError(
                    "pricingLines requires async execution (external pricing API). Use async tool call or provide pricingCatalog."
                )
            cost_estimate = _compute_cost_estimate(
                pricing_lines=pricing_lines_list,
                catalog_items=items,
                baseline_reference_total=baselineReferenceTotalMonthlyCost,
            )

        if cost_estimate is not None:
            updates["costEstimates"] = [cost_estimate]

        payload_json = json.dumps(updates, ensure_ascii=False, indent=2)
        return (
            f"Recorded IaC/cost artifacts at {_now_iso()} (iacFiles={len(iac_files_list)}, pricingLines={len(pricing_lines_list)}).\n"
            "\n"
            "AAA_STATE_UPDATE\n"
            "```json\n"
            f"{payload_json}\n"
            "```"
        )

    async def _arun(self, **kwargs: Any) -> str:
        # Same as _run, but allows calling the external pricing API.
        iac_files = kwargs.get("iacFiles") or []
        validation_results = kwargs.get("validationResults") or []
        pricing_lines = kwargs.get("pricingLines") or []
        pricing_catalog = kwargs.get("pricingCatalog")
        baseline_reference_total = kwargs.get("baselineReferenceTotalMonthlyCost")

        updates: Dict[str, Any] = {}

        if iac_files or validation_results:
            iac_artifact_id = str(uuid.uuid4())
            updates["iacArtifacts"] = [
                {
                    "id": iac_artifact_id,
                    "createdAt": _now_iso(),
                    "files": iac_files,
                    "validationResults": validation_results,
                }
            ]

        if pricing_lines:
            items = pricing_catalog
            if items is None:
                client = AzureRetailPricesClient()
                # Query per line with a narrow filter to reduce payload.
                items = []
                for line in pricing_lines:
                    service = str(line.get("serviceName") or "").strip().replace("'", "''")
                    region = str(line.get("armRegionName") or "").strip().replace("'", "''")
                    if not service or not region:
                        continue
                    filter_expr = f"serviceName eq '{service}' and armRegionName eq '{region}'"
                    line_items = await client.query_all(filter_expr=filter_expr)
                    items.extend(line_items)

            cost_estimate = _compute_cost_estimate(
                pricing_lines=pricing_lines,
                catalog_items=items,
                baseline_reference_total=baseline_reference_total,
            )
            updates["costEstimates"] = [cost_estimate]

        payload = json.dumps(updates, ensure_ascii=False, indent=2)
        return (
            f"Recorded IaC/cost artifacts at {_now_iso()} (iacFiles={len(iac_files)}, pricingLines={len(pricing_lines)}).\n"
            "\n"
            "AAA_STATE_UPDATE\n"
            "```json\n"
            f"{payload}\n"
            "```"
        )


def _compute_cost_estimate(
    *,
    pricing_lines: List[Dict[str, Any]],
    catalog_items: List[Dict[str, Any]],
    baseline_reference_total: Optional[float],
) -> Dict[str, Any]:
    estimate_id = str(uuid.uuid4())
    currency: Optional[str] = None

    line_items: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []
    total = 0.0

    for line in pricing_lines:
        name = str(line.get("name") or "").strip() or "line"
        qty = float(line.get("monthlyQuantity") or 0)
        if qty <= 0:
            continue

        request = PricingMatchRequest(
            service_name=str(line.get("serviceName") or "").strip(),
            arm_region_name=str(line.get("armRegionName") or "").strip(),
            sku_name=(str(line.get("skuName") or "").strip() or None),
            product_name_contains=(str(line.get("productNameContains") or "").strip() or None),
            meter_name_contains=(str(line.get("meterNameContains") or "").strip() or None),
        )

        match = find_best_retail_price_item(catalog_items, request)
        if not match:
            gaps.append({"name": name, "reason": "no_match", "request": line})
            continue

        unit_price = extract_unit_price(match)
        if unit_price is None:
            gaps.append({"name": name, "reason": "missing_unit_price", "request": line})
            continue

        currency = currency or extract_currency(match)

        monthly_cost = unit_price * qty
        total += monthly_cost
        line_items.append(
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "serviceName": match.get("serviceName"),
                "productName": match.get("productName"),
                "meterName": match.get("meterName"),
                "skuName": match.get("armSkuName") or match.get("skuName"),
                "unitOfMeasure": match.get("unitOfMeasure"),
                "unitPrice": unit_price,
                "monthlyQuantity": qty,
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


def create_iac_tools() -> List[BaseTool]:
    return [AAAGenerateIacTool()]
