"""Azure Retail Prices API client.

User Story 5 (T050): Provide a lightweight client for the public Azure Retail
Prices API with pagination, filtering, and retry behavior.

API base:
- https://prices.azure.com/api/retail/prices

This module intentionally keeps responses as dictionaries to avoid coupling to
a brittle schema. Callers should treat missing fields as expected.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx


DEFAULT_BASE_URL = "https://prices.azure.com/api/retail/prices"


@dataclass(frozen=True)
class RetailPricesQueryResult:
    items: List[Dict[str, Any]]
    next_page_link: Optional[str]


class AzureRetailPricesClient:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout_seconds
        self._max_retries = max_retries

    async def _get_json(self, url: str, *, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        last_exc: Optional[Exception] = None
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(self._max_retries + 1):
                try:
                    response = await client.get(url, params=params)
                    if response.status_code in (429, 500, 502, 503, 504):
                        retry_after = response.headers.get("Retry-After")
                        delay = float(retry_after) if retry_after and retry_after.isdigit() else (0.5 * (2**attempt))
                        await asyncio.sleep(min(delay, 8.0))
                        continue
                    response.raise_for_status()
                    return response.json()
                except Exception as exc:  # noqa: BLE001 - deliberate normalization
                    last_exc = exc
                    await asyncio.sleep(min(0.5 * (2**attempt), 8.0))

        raise RuntimeError(f"Azure Retail Prices API request failed after retries: {last_exc}")

    async def query_once(self, *, filter_expr: str, top: int = 1000) -> RetailPricesQueryResult:
        params: Dict[str, Any] = {"$filter": filter_expr, "$top": top}
        data = await self._get_json(self._base_url, params=params)
        items = data.get("Items") or data.get("items") or []
        next_link = data.get("NextPageLink") or data.get("nextPageLink")
        if not isinstance(items, list):
            items = []
        return RetailPricesQueryResult(items=items, next_page_link=next_link)

    async def query_all(self, *, filter_expr: str, top: int = 1000, max_pages: int = 25) -> List[Dict[str, Any]]:
        """Query and return all items following pagination.

        The API can return very large result sets; callers should provide a narrow filter.
        """
        results: List[Dict[str, Any]] = []
        page = await self.query_once(filter_expr=filter_expr, top=top)
        results.extend(page.items)

        next_link = page.next_page_link
        pages = 1
        while next_link:
            if pages >= max_pages:
                break
            data = await self._get_json(next_link)
            items = data.get("Items") or data.get("items") or []
            next_link = data.get("NextPageLink") or data.get("nextPageLink")
            if isinstance(items, list):
                results.extend(items)
            pages += 1

        return results
