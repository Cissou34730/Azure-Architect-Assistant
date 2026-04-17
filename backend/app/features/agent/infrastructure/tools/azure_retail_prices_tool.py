"""Standalone Azure Retail Prices tool for grounded pricing lookups."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr
from pydantic.alias_generators import to_camel

from app.shared.pricing.retail_prices_client import AzureRetailPricesClient

_TOOL_MODEL_CONFIG = ConfigDict(
    populate_by_name=True,
    alias_generator=to_camel,
    extra="forbid",
)


class AzureRetailPricesToolInput(BaseModel):
    """Request contract for Azure Retail Prices lookups."""

    model_config = _TOOL_MODEL_CONFIG

    service_name: str = Field(min_length=1)
    region: str = Field(min_length=1)
    sku_name: str | None = None
    product_name_contains: str | None = None
    meter_name_contains: str | None = None
    currency_code: str = Field(default="USD", min_length=3, max_length=3)


class AzureRetailPricesTool(BaseTool):
    """Tool that queries the public Azure Retail Prices API with simple caching."""

    name: str = "azure_retail_prices"
    description: str = (
        "Query the public Azure Retail Prices API for structured price items by service, region, and optional SKU. "
        "Use this for grounded Azure pricing data instead of relying on memory."
    )
    args_schema: type[BaseModel] = AzureRetailPricesToolInput

    _client: Any = PrivateAttr()
    _cache: dict[tuple[str, ...], tuple[float, dict[str, Any]]] = PrivateAttr(default_factory=dict)
    _cache_ttl_seconds: int = PrivateAttr(default=3600)

    def __init__(
        self,
        *,
        client: Any | None = None,
        cache_ttl_seconds: int = 3600,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._client = client or AzureRetailPricesClient()
        self._cache_ttl_seconds = cache_ttl_seconds

    def _run(self, payload: str | dict[str, Any] | None = None, **kwargs: Any) -> str:
        return asyncio.run(self._arun(payload=payload, **kwargs))

    async def _arun(self, payload: str | dict[str, Any] | None = None, **kwargs: Any) -> str:
        result = await self.lookup_prices(payload or kwargs)
        return json.dumps(result, ensure_ascii=False)

    async def lookup_prices(self, payload: str | dict[str, Any] | AzureRetailPricesToolInput) -> dict[str, Any]:
        request = self._parse_request(payload)
        cache_key = self._cache_key_for(request)
        cached = self._cache.get(cache_key)
        now = time.monotonic()
        if cached is not None and now - cached[0] < self._cache_ttl_seconds:
            cached_payload = dict(cached[1])
            cached_payload["fromCache"] = True
            return cached_payload

        filter_expr = _build_filter_expression(request)
        items, meta = await self._client.query_all_with_meta(filter_expr=filter_expr, max_pages=25)
        result = {
            "query": request.model_dump(mode="json", by_alias=True),
            "filterExpr": filter_expr,
            "currencyCode": request.currency_code.upper(),
            "itemCount": len(items),
            "items": [dict(item) for item in items if isinstance(item, dict)],
            "meta": meta,
            "fromCache": False,
        }
        self._cache[cache_key] = (now, dict(result))
        return result

    def _parse_request(
        self, payload: str | dict[str, Any] | AzureRetailPricesToolInput
    ) -> AzureRetailPricesToolInput:
        if isinstance(payload, AzureRetailPricesToolInput):
            return payload
        if isinstance(payload, str):
            return AzureRetailPricesToolInput.model_validate_json(payload)
        return AzureRetailPricesToolInput.model_validate(payload)

    @staticmethod
    def _cache_key_for(request: AzureRetailPricesToolInput) -> tuple[str, ...]:
        return (
            request.service_name.strip().lower(),
            request.region.strip().lower(),
            (request.sku_name or "").strip().lower(),
            (request.product_name_contains or "").strip().lower(),
            (request.meter_name_contains or "").strip().lower(),
            request.currency_code.strip().upper(),
        )


def _build_filter_expression(request: AzureRetailPricesToolInput) -> str:
    filters = [
        f"serviceName eq '{_escape_filter_value(request.service_name)}'",
        f"armRegionName eq '{_escape_filter_value(request.region)}'",
        f"currencyCode eq '{_escape_filter_value(request.currency_code.upper())}'",
    ]
    if request.sku_name:
        filters.append(f"skuName eq '{_escape_filter_value(request.sku_name)}'")
    return " and ".join(filters)


def _escape_filter_value(value: str) -> str:
    return value.replace("'", "''").strip()


__all__ = ["AzureRetailPricesTool", "AzureRetailPricesToolInput"]
