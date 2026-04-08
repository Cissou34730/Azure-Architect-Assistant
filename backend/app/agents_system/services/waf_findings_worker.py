"""LLM-backed worker that turns WAF evaluator output into remediation findings."""

from __future__ import annotations

import inspect
import json
import re
from collections import defaultdict
from collections.abc import Awaitable, Callable, Mapping
from copy import deepcopy
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel

from app.agents_system.config.prompt_loader import PromptLoader
from app.agents_system.services.source_logging import new_mcp_citation, new_reference_citation
from app.shared.ai import llm_service

_ACTIONABLE_STATUSES = frozenset({"open", "in_progress"})
_REFERENCE_DOCUMENT_PATH = re.compile(r"^referenceDocuments\[(?P<index>\d+)\]")
_MCP_QUERY_PATH = re.compile(r"^mcpQueries\[(?P<index>\d+)\]")


class FindingsGenerator(Protocol):
    def __call__(
        self, system_prompt: str, user_prompt: str
    ) -> dict[str, Any] | str | Awaitable[dict[str, Any] | str]: ...


class _GeneratedFinding(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel, extra="forbid")

    title: str
    severity: str
    description: str
    remediation: str
    impacted_components: list[str] = Field(default_factory=list)
    waf_pillar: str
    waf_topic: str
    waf_checklist_item_id: str
    source_citations: list[dict[str, Any]] = Field(default_factory=list)


class _GeneratedFindingsEnvelope(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel, extra="forbid")

    findings: list[_GeneratedFinding] = Field(default_factory=list)


class WAFFindingsWorker:
    """Generate remediation-oriented findings for actionable WAF checklist gaps."""

    def __init__(
        self,
        *,
        generator: FindingsGenerator | None = None,
        prompt_loader: PromptLoader | None = None,
        id_factory: Callable[[str], str] | None = None,
    ) -> None:
        self._generator = generator or self._default_generator
        self._prompt_loader = prompt_loader or PromptLoader.get_instance()
        self._id_factory = id_factory or (lambda item_id: f"finding-{item_id}")

    async def generate_findings(
        self,
        *,
        evaluator_result: Mapping[str, Any],
        architecture_state: Mapping[str, Any],
    ) -> dict[str, Any]:
        actionable_items = self._actionable_items(evaluator_result)
        if not actionable_items:
            return {"findings": [], "wafEvaluations": []}

        normalized_state = self._coerce_project_state(architecture_state)
        prompt = self._prompt_loader.load_prompt("waf_validator.yaml")
        system_prompt = str(prompt.get("system_prompt") or "").strip()
        user_prompt = self._build_user_prompt(
            actionable_items=actionable_items,
            evaluator_result=evaluator_result,
            architecture_state=normalized_state,
        )
        raw_response = await self._invoke_generator(system_prompt=system_prompt, user_prompt=user_prompt)
        generated = self._parse_generator_response(raw_response)

        findings: list[dict[str, Any]] = []
        finding_ids_by_item: dict[str, list[str]] = defaultdict(list)
        citations_by_item: dict[str, list[dict[str, Any]]] = defaultdict(list)
        citations_seen_by_item: dict[str, set[str]] = defaultdict(set)

        items_by_id = {str(item["itemId"]): item for item in actionable_items}
        for finding in generated.findings:
            item_id = finding.waf_checklist_item_id.strip()
            item = items_by_id.get(item_id)
            if item is None:
                raise ValueError(f"Generated finding references unknown checklist item '{item_id}'.")
            if finding_ids_by_item[item_id]:
                raise ValueError(
                    f"Generated multiple findings for actionable checklist item '{item_id}'."
                )

            finding_id = self._id_factory(item_id)
            citations = self._normalize_citations(
                citations=finding.source_citations,
                item=item,
                architecture_state=normalized_state,
            )
            if not citations:
                raise ValueError(
                    f"Generated finding for checklist item '{item_id}' does not include a source citation."
                )

            finding_payload = {
                "id": finding_id,
                "title": finding.title.strip(),
                "severity": finding.severity.strip().lower(),
                "description": finding.description.strip(),
                "remediation": finding.remediation.strip(),
                "impactedComponents": [component.strip() for component in finding.impacted_components if component.strip()],
                "wafPillar": finding.waf_pillar.strip(),
                "wafTopic": finding.waf_topic.strip(),
                "wafChecklistItemId": item_id,
                "sourceCitations": citations,
            }
            findings.append(finding_payload)
            finding_ids_by_item[item_id].append(finding_id)
            for citation in citations:
                citation_id = str(citation.get("id") or "").strip()
                if citation_id and citation_id not in citations_seen_by_item[item_id]:
                    citations_by_item[item_id].append(citation)
                    citations_seen_by_item[item_id].add(citation_id)

        missing_item_ids = sorted(
            item_id for item_id in items_by_id if not finding_ids_by_item[item_id]
        )
        if missing_item_ids:
            raise ValueError(
                "Generated missing findings for actionable checklist items: "
                + ", ".join(missing_item_ids)
            )

        waf_evaluations = [
            {
                "itemId": item_id,
                "pillar": str(item["pillar"]).strip(),
                "topic": str(item["topic"]).strip(),
                "status": str(item["status"]).strip().lower(),
                "evidence": self._build_evidence_summary(item),
                "relatedFindingIds": finding_ids_by_item[item_id],
                "sourceCitations": citations_by_item[item_id],
            }
            for item_id, item in items_by_id.items()
            if finding_ids_by_item[item_id]
        ]

        return {
            "findings": findings,
            "wafEvaluations": waf_evaluations,
        }

    async def _default_generator(self, system_prompt: str, user_prompt: str) -> str:
        return await llm_service.get_llm_service()._complete(  # pyright: ignore[reportPrivateUsage]
            system_prompt,
            user_prompt,
            max_tokens=2000,
        )

    async def _invoke_generator(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any] | str:
        result = self._generator(system_prompt, user_prompt)
        if inspect.isawaitable(result):
            result = await result
        return result

    def _parse_generator_response(
        self, response: dict[str, Any] | str
    ) -> _GeneratedFindingsEnvelope:
        payload = response
        if isinstance(response, str):
            payload = json.loads(response)
        if not isinstance(payload, dict):
            raise ValueError("WAF findings generator returned an invalid payload.")
        try:
            return _GeneratedFindingsEnvelope.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

    def _build_user_prompt(
        self,
        *,
        actionable_items: list[dict[str, Any]],
        evaluator_result: Mapping[str, Any],
        architecture_state: Mapping[str, Any],
    ) -> str:
        response_contract = {
            "findings": [
                {
                    "title": "string",
                    "severity": "critical|high|medium|low",
                    "description": "string",
                    "remediation": "string",
                    "impactedComponents": ["string"],
                    "wafPillar": "string",
                    "wafTopic": "string",
                    "wafChecklistItemId": "string",
                    "sourceCitations": [
                        {
                            "id": "string",
                            "kind": "referenceDocument|mcp",
                            "referenceDocumentId": "string|null",
                            "mcpQueryId": "string|null",
                            "url": "string|null",
                            "note": "string|null",
                        }
                    ],
                }
            ]
        }
        payload = {
            "actionableItems": actionable_items,
            "summary": evaluator_result.get("summary") or {},
            "architectureState": {
                key: deepcopy(architecture_state.get(key))
                for key in (
                    "requirements",
                    "assumptions",
                    "candidateArchitectures",
                    "adrs",
                    "diagrams",
                    "referenceDocuments",
                    "mcpQueries",
                )
                if architecture_state.get(key) is not None
            },
            "responseContract": response_contract,
        }
        return (
            "Return JSON only.\n"
            "Use the responseContract exactly.\n"
            "Create remediation-focused findings for every actionable checklist item.\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )

    def _actionable_items(self, evaluator_result: Mapping[str, Any]) -> list[dict[str, Any]]:
        raw_items = evaluator_result.get("items")
        if not isinstance(raw_items, list):
            return []
        actionable: list[dict[str, Any]] = []
        for item in raw_items:
            if not isinstance(item, Mapping):
                continue
            status = str(item.get("status") or "").strip().lower()
            if status not in _ACTIONABLE_STATUSES:
                continue
            item_id = str(item.get("itemId") or "").strip()
            pillar = str(item.get("pillar") or "").strip()
            topic = str(item.get("topic") or "").strip()
            if not item_id or not pillar or not topic:
                continue
            actionable.append(
                {
                    "itemId": item_id,
                    "pillar": pillar,
                    "topic": topic,
                    "status": status,
                    "coverageScore": item.get("coverageScore", 0.0),
                    "matchedSourcePaths": list(item.get("matchedSourcePaths") or []),
                    "evidence": list(item.get("evidence") or []),
                }
            )
        return actionable

    def _coerce_project_state(self, state: Mapping[str, Any]) -> Mapping[str, Any]:
        nested_state = state.get("current_project_state")
        if isinstance(nested_state, Mapping):
            return nested_state
        return state

    def _normalize_citations(
        self,
        *,
        citations: list[dict[str, Any]],
        item: Mapping[str, Any],
        architecture_state: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for citation in citations:
            if not isinstance(citation, Mapping):
                continue
            citation_id = str(citation.get("id") or "").strip()
            if citation_id and citation_id not in seen_ids:
                normalized.append(dict(citation))
                seen_ids.add(citation_id)

        if normalized:
            return normalized

        for path in item.get("matchedSourcePaths") or []:
            if not isinstance(path, str):
                continue
            derived = self._citation_from_path(
                path=path,
                item=item,
                architecture_state=architecture_state,
            )
            if not derived:
                continue
            citation_id = str(derived.get("id") or "").strip()
            if citation_id and citation_id not in seen_ids:
                normalized.append(derived)
                seen_ids.add(citation_id)
        return normalized

    def _citation_from_path(
        self,
        *,
        path: str,
        item: Mapping[str, Any],
        architecture_state: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        reference_match = _REFERENCE_DOCUMENT_PATH.match(path)
        if reference_match:
            documents = architecture_state.get("referenceDocuments")
            if isinstance(documents, list):
                index = int(reference_match.group("index"))
                if 0 <= index < len(documents) and isinstance(documents[index], Mapping):
                    document = documents[index]
                    document_id = str(document.get("id") or "").strip()
                    if document_id:
                        return new_reference_citation(
                            reference_document_id=document_id,
                            url=self._optional_text(document.get("url")),
                            note=str(item.get("topic") or "").strip() or None,
                            citation_id=f"ref-{document_id}",
                        ).model_dump(mode="json", by_alias=True, exclude_none=True)

        mcp_match = _MCP_QUERY_PATH.match(path)
        if mcp_match:
            queries = architecture_state.get("mcpQueries")
            if isinstance(queries, list):
                index = int(mcp_match.group("index"))
                if 0 <= index < len(queries) and isinstance(queries[index], Mapping):
                    query = queries[index]
                    query_id = str(query.get("id") or "").strip()
                    if query_id:
                        urls = query.get("resultUrls")
                        url = urls[0] if isinstance(urls, list) and urls else None
                        return new_mcp_citation(
                            mcp_query_id=query_id,
                            url=self._optional_text(url),
                            note=str(item.get("topic") or "").strip() or None,
                            citation_id=f"mcp-{query_id}",
                        ).model_dump(mode="json", by_alias=True, exclude_none=True)

        return None

    def _build_evidence_summary(self, item: Mapping[str, Any]) -> str:
        status = str(item.get("status") or "").strip().lower()
        coverage_score = item.get("coverageScore", 0.0)
        return (
            "Deterministic WAF evaluator marked this checklist item as "
            f"{status} (coverageScore={coverage_score})."
        )

    def _optional_text(self, value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None


__all__ = ["WAFFindingsWorker"]
