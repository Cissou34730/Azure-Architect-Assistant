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
import random
import time
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://prices.azure.com/api/retail/prices"


@dataclass(frozen=True)
class RetailPricesQueryResult:
    items: list[dict[str, Any]]
    next_page_link: str | None


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
        # Note: In this codebase, "max_retries" is treated as a *maximum attempts*
        # budget (including the first attempt). This matches our E2E policy:
        # 3 attempts then fail.
        self._max_attempts = max_retries

    def _backoff_seconds(self, attempt_number: int) -> float:
        # attempt_number is 1-based
        base = min(0.5 * (2 ** max(attempt_number - 1, 0)), 8.0)
        jitter = random.uniform(0.0, 0.25)
        return min(base + jitter, 8.0)

    async def _get_json_with_meta(
        self, url: str, *, params: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """GET JSON with strict attempt budget and timing metadata.

        Returns (data, meta).
        """
        last_exc: Exception | None = None
        attempts_meta: list[dict[str, Any]] = []
        start_total = time.perf_counter()

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt_number in range(1, self._max_attempts + 1):
                start_attempt = time.perf_counter()
                try:
                    response = await client.get(url, params=params)
                    elapsed_ms = (time.perf_counter() - start_attempt) * 1000.0
                    attempts_meta.append(
                        {
                            "attempt": attempt_number,
                            "statusCode": response.status_code,
                            "latencyMs": round(elapsed_ms, 2),
                        }
                    )

                    if response.status_code in (429, 500, 502, 503, 504):
                        retry_after = response.headers.get("Retry-After")
                        if retry_after and retry_after.isdigit():
                            delay = float(retry_after)
                        else:
                            delay = self._backoff_seconds(attempt_number)

                        if attempt_number < self._max_attempts:
                            await asyncio.sleep(delay)
                            continue

                    response.raise_for_status()
                    data = response.json()
                    total_ms = (time.perf_counter() - start_total) * 1000.0
                    return (
                        data,
                        {
                            "url": url,
                            "params": params or {},
                            "attempts": attempt_number,
                            "totalLatencyMs": round(total_ms, 2),
                            "attemptDetails": attempts_meta,
                            "error": None,
                        },
                    )
                except Exception as exc:  # noqa: BLE001 - deliberate normalization
                    elapsed_ms = (time.perf_counter() - start_attempt) * 1000.0
                    last_exc = exc
                    attempts_meta.append(
                        {
                            "attempt": attempt_number,
                            "statusCode": None,
                            "latencyMs": round(elapsed_ms, 2),
                            "error": str(exc),
                        }
                    )
                    if attempt_number < self._max_attempts:
                        await asyncio.sleep(self._backoff_seconds(attempt_number))

        total_ms = (time.perf_counter() - start_total) * 1000.0
        raise RuntimeError(
            "Azure Retail Prices API request failed after attempts: "
            f"{self._max_attempts}. Last error: {last_exc} (total {total_ms:.2f}ms)"
        )

    async def _get_json(self, url: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        data, _meta = await self._get_json_with_meta(url, params=params)
        return data

    async def query_once(self, *, filter_expr: str, top: int = 1000) -> RetailPricesQueryResult:
        params: dict[str, Any] = {"$filter": filter_expr, "$top": top}
        data = await self._get_json(self._base_url, params=params)
        items = data.get("Items") or data.get("items") or []
        next_link = data.get("NextPageLink") or data.get("nextPageLink")
        if not isinstance(items, list):
            items = []
        return RetailPricesQueryResult(items=items, next_page_link=next_link)

    async def query_once_with_meta(
        self, *, filter_expr: str, top: int = 1000
    ) -> tuple[RetailPricesQueryResult, dict[str, Any]]:
        params: dict[str, Any] = {"$filter": filter_expr, "$top": top}
        data, meta = await self._get_json_with_meta(self._base_url, params=params)
        items = data.get("Items") or data.get("items") or []
        next_link = data.get("NextPageLink") or data.get("nextPageLink")
        if not isinstance(items, list):
            items = []
        return RetailPricesQueryResult(items=items, next_page_link=next_link), meta

    async def query_all(self, *, filter_expr: str, top: int = 1000, max_pages: int = 25) -> list[dict[str, Any]]:
        """Query and return all items following pagination.

        The API can return very large result sets; callers should provide a narrow filter.
        """
        results: list[dict[str, Any]] = []
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

    async def query_all_with_meta(
        self, *, filter_expr: str, top: int = 1000, max_pages: int = 25
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Query and return all items plus per-request metadata."""
        results: list[dict[str, Any]] = []
        request_metas: list[dict[str, Any]] = []

        page, meta = await self.query_once_with_meta(filter_expr=filter_expr, top=top)
        request_metas.append(meta)
        results.extend(page.items)

        next_link = page.next_page_link
        pages = 1
        while next_link:
            if pages >= max_pages:
                break
            data, meta = await self._get_json_with_meta(next_link)
            request_metas.append(meta)
            items = data.get("Items") or data.get("items") or []
            next_link = data.get("NextPageLink") or data.get("nextPageLink")
            if isinstance(items, list):
                results.extend(items)
            pages += 1

        total_latency_ms = round(sum(m.get("totalLatencyMs", 0.0) for m in request_metas), 2)
        return (
            results,
            {
                "filterExpr": filter_expr,
                "pages": pages,
                "requests": request_metas,
                "totalLatencyMs": total_latency_ms,
            },
        )

