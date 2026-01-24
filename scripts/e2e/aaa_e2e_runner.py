from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import sqlite3
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import httpx

logger = logging.getLogger(__name__)


_SCENARIOS_ROOT = Path(__file__).resolve().parent / "scenarios"
_GOLDENS_ROOT = Path(__file__).resolve().parent / "goldens"
_RUNS_ROOT = Path(__file__).resolve().parent / "runs"


@dataclass(frozen=True)
class ScenarioDocument:
    path: str
    content_type: str


@dataclass(frozen=True)
class ScenarioTurn:
    id: str
    message: str


@dataclass(frozen=True)
class ScenarioSpec:
    id: str
    name: str
    project_name: str
    documents: list[ScenarioDocument]
    chat_turns: list[ScenarioTurn]
    assertions: dict[str, Any]


@dataclass(frozen=True)
class RunnerConfig:
    mode: Literal["in-process", "remote"]
    base_url: str
    scenario_id: str
    update_goldens: bool
    timeout_s: float
    kb_root: str | None = None


def _deep_get(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_scenario(scenario_id: str) -> ScenarioSpec:
    scenario_dir = _SCENARIOS_ROOT / scenario_id
    spec_path = scenario_dir / "scenario.json"
    if not spec_path.exists():
        raise FileNotFoundError(f"Scenario not found: {spec_path}")

    raw = json.loads(spec_path.read_text(encoding="utf-8"))

    documents = [
        ScenarioDocument(path=d["path"], content_type=d.get("contentType", "text/plain"))
        for d in raw.get("documents", [])
    ]
    turns = [ScenarioTurn(id=t["id"], message=t["message"]) for t in raw.get("chatTurns", [])]

    scenario = ScenarioSpec(
        id=raw["id"],
        name=raw["name"],
        project_name=raw["projectName"],
        documents=documents,
        chat_turns=turns,
        assertions=dict(raw.get("assertions", {})),
    )

    validate_scenario(scenario, scenario_dir=scenario_dir)
    return scenario


def validate_scenario(scenario: ScenarioSpec, *, scenario_dir: Path) -> None:
    if not scenario.id:
        raise ValueError("scenario.id is required")
    if not scenario.project_name:
        raise ValueError("scenario.projectName is required")
    if not scenario.documents:
        raise ValueError("scenario.documents must not be empty")
    if not scenario.chat_turns:
        raise ValueError("scenario.chatTurns must not be empty")

    for doc in scenario.documents:
        if not (scenario_dir / doc.path).exists():
            raise FileNotFoundError(f"Missing scenario document: {scenario_dir / doc.path}")

    for turn in scenario.chat_turns:
        if not turn.id.strip():
            raise ValueError("chatTurns[].id must not be empty")
        if not turn.message.strip():
            raise ValueError("chatTurns[].message must not be empty")


def apply_required_env() -> None:
    os.environ.setdefault("AAA_AGENT_ENGINE", "langgraph")
    os.environ.setdefault("AAA_ENABLE_STAGE_ROUTING", "true")


def apply_optional_kb_root_override(kb_root: str | None) -> None:
    if not kb_root:
        return
    os.environ["KNOWLEDGE_BASES_ROOT"] = kb_root


def _parse_aaa_log_blocks(text: str, marker: str) -> list[dict[str, Any]]:
    """Extract structured JSON blocks embedded in tool output.

    We expect blocks like:
    - AAA_MCP_LOG\n```json\n{...}\n```
    - AAA_PRICING_LOG\n```json\n{...}\n```
    """
    if not text:
        return []

    pattern = re.compile(
        rf"{re.escape(marker)}\s*\n```json\n(?P<payload>\{{.*?\}})\n```",
        re.DOTALL,
    )

    blocks: list[dict[str, Any]] = []
    for match in pattern.finditer(text):
        payload_raw = match.group("payload")
        try:
            blocks.append(json.loads(payload_raw))
        except json.JSONDecodeError:
            continue
    return blocks


def _summarize_state(state: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "keys": sorted(state),
        "counts": {},
    }

    for key in [
        "requirements",
        "ambiguities",
        "adrs",
        "diagrams",
        "findings",
        "traceabilityLinks",
        "traceabilityIssues",
    ]:
        value = state.get(key)
        if value is None:
            snake = {
                "traceabilityLinks": "traceability_links",
                "traceabilityIssues": "traceability_issues",
            }.get(key)
            if snake:
                value = state.get(snake)
        if isinstance(value, list):
            summary["counts"][key] = len(value)

    coverage = state.get("mindMapCoverage")
    if coverage is None:
        coverage = state.get("mind_map_coverage")
    if isinstance(coverage, dict):
        topics = coverage.get("topics")
        if isinstance(topics, dict):
            status_counts: dict[str, int] = {}
            for topic_val in topics.values():
                if isinstance(topic_val, dict):
                    status = str(topic_val.get("status") or "unknown")
                    status_counts[status] = status_counts.get(status, 0) + 1
            summary["mindMapCoverage"] = {
                "topicCount": len(topics),
                "statusCounts": status_counts,
            }

    conflicts = state.get("conflicts")
    if isinstance(conflicts, list):
        summary["counts"]["conflicts"] = len(conflicts)

    return summary


def normalize_report_for_golden(report: dict[str, Any]) -> dict[str, Any]:
    """Drop high-variance fields so golden diffs are meaningful."""
    normalized = json.loads(json.dumps(report))

    for key in ["runId", "generatedAt", "projectId"]:
        normalized.pop(key, None)

    steps = normalized.get("steps")
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict):
                step.pop("answer", None)
                step.pop("answerHash", None)
                step.pop("mcpLogs", None)
                step.pop("pricingLogs", None)
                step.pop("durationMs", None)

    return normalized


def _assert_required_state_keys(state: dict[str, Any], required: Iterable[str]) -> list[str]:
    # Frontend adapts backend snake_case <-> camelCase. The E2E runner needs to
    # accept either representation without forcing backend casing changes.
    alias_map = {
        "mindMapCoverage": "mind_map_coverage",
        "traceabilityLinks": "traceability_links",
        "traceabilityIssues": "traceability_issues",
        "clarificationQuestions": "clarification_questions",
        "candidateArchitectures": "candidate_architectures",
        "iacArtifacts": "iac_artifacts",
        "costEstimates": "cost_estimates",
        "iterationEvents": "iteration_events",
        "mcpQueries": "mcp_queries",
        "openQuestions": "open_questions",
        "lastUpdated": "last_updated",
    }
    missing: list[str] = []
    for key in required:
        if key in state:
            continue

        alt = alias_map.get(key)
        if alt and alt in state:
            continue

        missing.append(key)
    return missing


def _get_waf_checklist_items(state: dict[str, Any]) -> list[Any]:
    waf = state.get("wafChecklist")
    if waf is None:
        waf = state.get("waf_checklist")
    if not isinstance(waf, dict):
        return []
    items = waf.get("items")
    return items if isinstance(items, list) else []


def _count_kb_tool_calls(reasoning_steps: Any) -> int:
    if not isinstance(reasoning_steps, list):
        return 0
    count = 0
    for step in reasoning_steps:
        if not isinstance(step, dict):
            continue
        action = str(step.get("action") or "")
        if action == "kb_search" or action == "kb_search_agent" or action.startswith("kb_"):
            count += 1
    return count


async def _preflight_kb_query_service(client: httpx.AsyncClient) -> None:
    """Fail fast if KB query service can't see any indexed KBs.

    The ReAct loop must be able to consult WAF via the KB/LlamaIndex pipeline.
    If indexes aren't available on disk (or KNOWLEDGE_BASES_ROOT is misconfigured),
    the agent may degrade and never retrieve WAF content.
    """



    """Ensure KB subsystem is ready without invoking LLM-heavy queries."""

    try:
        response = await client.get("/api/kb/health")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "KB preflight failed: unable to call /api/kb/health. "
            "This usually means the backend app or routing isn't initialized correctly."
        ) from exc

    if response.status_code != 200:
        raise RuntimeError(
            f"KB preflight failed: /api/kb/health returned HTTP {response.status_code}: {response.text}"
        )

    payload = response.json()
    knowledge_bases = payload.get("knowledge_bases")
    if knowledge_bases is None:
        knowledge_bases = payload.get("knowledgeBases")
    if not isinstance(knowledge_bases, list):
        knowledge_bases = []

    any_ready = False
    for kb in knowledge_bases:
        if not isinstance(kb, dict):
            continue
        index_ready = kb.get("index_ready")
        if index_ready is None:
            index_ready = kb.get("indexReady")
        if index_ready is True:
            any_ready = True
            break

    if not any_ready:
        logger.warning(
            "KB preflight: no knowledge base index is ready. "
            "Tests will run but KB queries will fail. "
            "To fix: ingest WAF through the UI or use --kb-root."
        )


async def _http_json(client: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    resp = await client.request(method, url, **kwargs)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected non-object JSON response from {url}")
    return data


def _prepare_run_paths(*, run_id: str, scenario_id: str) -> tuple[Path, Path]:
    run_dir = _RUNS_ROOT / run_id / scenario_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir, run_dir / "transcript.jsonl"


def _finalize_report(*, report: dict[str, Any], run_id: str, scenario: ScenarioSpec, mode: str) -> dict[str, Any]:
    report["mode"] = mode
    report.update(
        {
            "runId": run_id,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "scenario": {"id": scenario.id, "name": scenario.name},
        }
    )
    return report


def _write_run_outputs(*, report: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    (run_dir / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    normalized = normalize_report_for_golden(report)
    (run_dir / "report.normalized.json").write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return normalized


def _assert_db_persistence(*, project_id: str, report: dict[str, Any]) -> dict[str, Any]:
    """Validate that project artifacts are persisted to SQLite databases.
    
    Args:
        project_id: Project ID to validate
        report: E2E run report to augment with DB assertion results
    
    Returns:
        DB assertion results dict with status and details
    """
    repo_root = Path(__file__).resolve().parents[2]
    projects_db_path = repo_root / "backend" / "data" / "projects.db"
    diagrams_db_path = repo_root / "backend" / "data" / "diagrams.db"
    
    results = {
        "projectId": project_id,
        "projectsDbPath": str(projects_db_path),
        "diagramsDbPath": str(diagrams_db_path),
        "assertions": {
            "projectRowExists": False,
            "projectStateRowExists": False,
            "wafChecklistNonEmpty": False,
            "adrsNonEmpty": False,
            "diagramsExist": False,
        },
        "details": {},
    }
    
    # Check projects.db
    if not projects_db_path.exists():
        results["error"] = f"projects.db not found at {projects_db_path}"
        return results
    
    try:
        conn = sqlite3.connect(str(projects_db_path))
        conn.row_factory = sqlite3.Row
        
        # Check project row
        cursor = conn.execute("SELECT id, name FROM project WHERE id = ?", (project_id,))
        project_row = cursor.fetchone()
        if project_row:
            results["assertions"]["projectRowExists"] = True
            results["details"]["projectName"] = project_row["name"]
        
        # Check project_state row
        cursor = conn.execute("SELECT state FROM project_state WHERE project_id = ?", (project_id,))
        state_row = cursor.fetchone()
        if state_row:
            results["assertions"]["projectStateRowExists"] = True
            
            # Parse state JSON
            try:
                state = json.loads(state_row["state"])
                
                # Check WAF checklist
                waf_checklist = state.get("wafChecklist", {})
                if isinstance(waf_checklist, dict):
                    items = waf_checklist.get("items", [])
                    if isinstance(items, list) and len(items) > 0:
                        results["assertions"]["wafChecklistNonEmpty"] = True
                        results["details"]["wafChecklistItemCount"] = len(items)
                
                # Check ADRs
                adrs = state.get("adrs", [])
                if isinstance(adrs, list) and len(adrs) > 0:
                    results["assertions"]["adrsNonEmpty"] = True
                    results["details"]["adrCount"] = len(adrs)
                
                # Check diagrams references
                diagrams = state.get("diagrams", [])
                if isinstance(diagrams, list) and len(diagrams) > 0:
                    results["details"]["diagramRefCount"] = len(diagrams)
                
            except json.JSONDecodeError:
                results["details"]["stateParseError"] = "Failed to parse state JSON"
        
        conn.close()
        
    except Exception as exc:
        results["error"] = f"projects.db query failed: {exc!s}"
        return results
    
    # Check diagrams.db
    if not diagrams_db_path.exists():
        results["details"]["diagramsDbNote"] = f"diagrams.db not found at {diagrams_db_path}"
        return results
    
    try:
        conn = sqlite3.connect(str(diagrams_db_path))
        conn.row_factory = sqlite3.Row
        
        # Count diagram rows (we don't have adr_id to filter directly, so count all)
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM diagram")
        row = cursor.fetchone()
        if row and row["cnt"] > 0:
            results["assertions"]["diagramsExist"] = True
            results["details"]["diagramRowCount"] = row["cnt"]
        
        conn.close()
        
    except Exception as exc:
        results["details"]["diagramsDbError"] = f"diagrams.db query failed: {exc!s}"
    
    # Compute overall pass/fail
    assertions = results["assertions"]
    all_pass = all([
        assertions["projectRowExists"],
        assertions["projectStateRowExists"],
        # Note: not requiring WAF/ADRs/diagrams for initial implementation
        # These will be tested once persistence tools are working
    ])
    
    results["status"] = "PASS" if all_pass else "FAIL"
    return results


def _compare_or_update_golden(
    *, scenario_id: str, normalized: dict[str, Any], run_dir: Path, update_goldens: bool
) -> str:
    _GOLDENS_ROOT.mkdir(parents=True, exist_ok=True)
    golden_dir = _GOLDENS_ROOT / scenario_id
    golden_dir.mkdir(parents=True, exist_ok=True)
    golden_path = golden_dir / "report.normalized.json"

    if update_goldens or not golden_path.exists():
        golden_path.write_text(
            json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return "updated" if update_goldens else "initialized"

    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    if golden != normalized:
        (run_dir / "golden_diff.txt").write_text(
            _format_simple_diff(golden, normalized), encoding="utf-8"
        )
        return "mismatch"
    return "match"


async def _run_remote(
    *, base_url: str, timeout_s: float, scenario: ScenarioSpec, transcript_path: Path
) -> dict[str, Any]:
    client = httpx.AsyncClient(base_url=base_url, timeout=timeout_s)
    try:
        return await _run_with_client(client, scenario, transcript_path)
    finally:
        await client.aclose()


async def _run_in_process(
    *, timeout_s: float, scenario: ScenarioSpec, transcript_path: Path
) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    backend_root = repo_root / "backend"
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    from app.core.app_settings import get_app_settings  # noqa: PLC0415

    get_app_settings.cache_clear()

    from app.main import app  # noqa: PLC0415

    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(
        transport=transport, base_url="http://test", timeout=timeout_s
    )

    try:
        lifespan_ctx = getattr(app.router, "lifespan_context", None)
        if lifespan_ctx is not None:
            async with lifespan_ctx(app):
                return await _run_with_client(client, scenario, transcript_path)

        await app.router.startup()
        try:
            return await _run_with_client(client, scenario, transcript_path)
        finally:
            await app.router.shutdown()
    finally:
        await client.aclose()


async def run_scenario(config: RunnerConfig) -> dict[str, Any]:
    apply_required_env()
    apply_optional_kb_root_override(config.kb_root)

    scenario = load_scenario(config.scenario_id)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    run_dir, transcript_path = _prepare_run_paths(run_id=run_id, scenario_id=scenario.id)

    if config.mode == "in-process":
        report = await _run_in_process(
            timeout_s=config.timeout_s, scenario=scenario, transcript_path=transcript_path
        )
        report = _finalize_report(report=report, run_id=run_id, scenario=scenario, mode="in-process")
    else:
        report = await _run_remote(
            base_url=config.base_url,
            timeout_s=config.timeout_s,
            scenario=scenario,
            transcript_path=transcript_path,
        )
        report = _finalize_report(report=report, run_id=run_id, scenario=scenario, mode="remote")

    # Add DB persistence assertions
    project_id = report.get("projectId")
    if project_id:
        db_assertions = _assert_db_persistence(project_id=project_id, report=report)
        report["dbPersistence"] = db_assertions
    
    normalized = _write_run_outputs(report=report, run_dir=run_dir)
    report["goldenStatus"] = _compare_or_update_golden(
        scenario_id=scenario.id,
        normalized=normalized,
        run_dir=run_dir,
        update_goldens=config.update_goldens,
    )
    return report


def _format_simple_diff(expected: Any, actual: Any) -> str:
    expected_text = json.dumps(expected, indent=2, sort_keys=True, ensure_ascii=False)
    actual_text = json.dumps(actual, indent=2, sort_keys=True, ensure_ascii=False)
    return "EXPECTED\n" + expected_text + "\n\nACTUAL\n" + actual_text + "\n"


def _evaluate_advisory_quality(answer: str, request: str) -> dict[str, Any]:
    """Evaluate agent's advisory quality on 4 dimensions (0-2 scale each).
    
    Args:
        answer: Agent's response text
        request: User's request text
    
    Returns:
        Dict with scores and total:
        {
            "proactivity": 0-2,
            "correction": 0-2,
            "evidence": 0-2,
            "clarity": 0-2,
            "total": 0-8,
            "details": {...}
        }
    """
    answer_lower = answer.lower()
    scores = {
        "proactivity": 0,
        "correction": 0,
        "evidence": 0,
        "clarity": 0,
    }
    details = {}
    
    # Proactivity (0-2): Does agent propose next steps, suggest improvements, or drive forward?
    proactivity_indicators = [
        "i recommend", "i suggest", "consider", "shall i", "shall we",
        "next step", "i propose", "you should", "you might want to",
        "missing", "not specified", "haven't specified", "notice you",
    ]
    proactive_count = sum(1 for indicator in proactivity_indicators if indicator in answer_lower)
    if proactive_count >= 3:
        scores["proactivity"] = 2
        details["proactivity"] = f"Strong proactivity ({proactive_count} indicators)"
    elif proactive_count >= 1:
        scores["proactivity"] = 1
        details["proactivity"] = f"Some proactivity ({proactive_count} indicators)"
    else:
        details["proactivity"] = "Passive response (no proactive indicators)"
    
    # Correction (0-2): Does agent challenge assumptions or point out issues?
    correction_indicators = [
        "however", "but", "contradict", "risk", "issue", "problem",
        "not recommended", "concern", "caution", "trade-off", "tradeoff",
        "instead", "alternative", "better to", "violation", "conflict",
    ]
    correction_count = sum(1 for indicator in correction_indicators if indicator in answer_lower)
    if correction_count >= 3:
        scores["correction"] = 2
        details["correction"] = f"Strong correction/challenge ({correction_count} indicators)"
    elif correction_count >= 1:
        scores["correction"] = 1
        details["correction"] = f"Some correction/challenge ({correction_count} indicators)"
    else:
        details["correction"] = "No challenges or corrections"
    
    # Evidence (0-2): Does agent provide citations, sources, or references?
    evidence_indicators = [
        "http://", "https://", "microsoft.com", "azure.com", "learn.microsoft",
        "documentation", "according to", "reference", "cited", "source:",
        "waf", "well-architected", "benchmark", "study", "guidance",
    ]
    evidence_count = sum(1 for indicator in evidence_indicators if indicator in answer_lower)
    if evidence_count >= 5:
        scores["evidence"] = 2
        details["evidence"] = f"Strong evidence ({evidence_count} references)"
    elif evidence_count >= 2:
        scores["evidence"] = 1
        details["evidence"] = f"Some evidence ({evidence_count} references)"
    else:
        details["evidence"] = "Minimal evidence/citations"
    
    # Clarity (0-2): Is the response structured and clear?
    # Check for structured formatting (headings, lists, sections)
    has_headings = "##" in answer or "###" in answer
    has_lists = answer.count("\n- ") >= 3 or answer.count("\n* ") >= 3 or answer.count("\n1.") >= 3
    has_sections = answer.count("\n\n") >= 3
    is_long_enough = len(answer) >= 200
    
    clarity_score = 0
    if has_headings and has_lists:
        clarity_score = 2
        details["clarity"] = "Well-structured (headings + lists)"
    elif has_headings or has_lists or has_sections:
        clarity_score = 1
        details["clarity"] = "Some structure (basic formatting)"
    elif is_long_enough:
        clarity_score = 1
        details["clarity"] = "Adequate length but minimal structure"
    else:
        details["clarity"] = "Brief or unstructured"
    scores["clarity"] = clarity_score
    
    total = sum(scores.values())
    
    return {
        **scores,
        "total": total,
        "maxTotal": 8,
        "passed": total >= 4,  # Pass threshold: avg >= 4/8
        "details": details,
    }


async def _run_with_client(
    client: httpx.AsyncClient, scenario: ScenarioSpec, transcript_path: Path
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []

    await _preflight_kb_query_service(client)

    # US0: create project
    created = await _http_json(client, "POST", "/api/projects", json={"name": scenario.project_name})
    project = created.get("project")
    if not isinstance(project, dict) or "id" not in project:
        raise ValueError("Create project response missing project.id")
    project_id = str(project["id"])

    # US0: upload documents
    scenario_dir = _SCENARIOS_ROOT / scenario.id
    files: list[tuple[str, tuple[str, bytes, str]]] = []
    for doc in scenario.documents:
        content = (scenario_dir / doc.path).read_bytes()
        filename = Path(doc.path).name
        files.append(("documents", (filename, content, doc.content_type)))

    await _http_json(client, "POST", f"/api/projects/{project_id}/documents", files=files)

    # US1: analyze docs
    analyzed = await _http_json(client, "POST", f"/api/projects/{project_id}/analyze-docs")
    state = analyzed.get("projectState")
    if not isinstance(state, dict):
        raise ValueError("analyze-docs response missing projectState")

    missing_keys = _assert_required_state_keys(
        state, scenario.assertions.get("requireStateKeys", [])
    )

    for turn in scenario.chat_turns:
        start = datetime.now(timezone.utc)

        # US7 hook: simulate authoritative human edit to ADR decision text.
        if turn.id == "us7-human-edit":
            await _apply_human_adr_append(client, project_id)

        response = await _http_json(
            client,
            "POST",
            f"/api/agent/projects/{project_id}/chat",
            json={"message": turn.message},
        )

        end = datetime.now(timezone.utc)
        duration_ms = int((end - start).total_seconds() * 1000)

        answer = str(response.get("answer") or "")
        reasoning_steps = response.get("reasoning_steps") or response.get("reasoningSteps")
        mcp_logs: list[dict[str, Any]] = []
        pricing_logs: list[dict[str, Any]] = []
        kb_call_count = 0

        if isinstance(reasoning_steps, list):
            for step in reasoning_steps:
                if not isinstance(step, dict):
                    continue
                obs = str(step.get("observation") or "")
                mcp_logs.extend(_parse_aaa_log_blocks(obs, "AAA_MCP_LOG"))
                pricing_logs.extend(_parse_aaa_log_blocks(obs, "AAA_PRICING_LOG"))

            kb_call_count = _count_kb_tool_calls(reasoning_steps)

        # Evaluate advisory quality
        advisory_quality = _evaluate_advisory_quality(answer, turn.message)

        step_record = {
            "id": turn.id,
            "request": turn.message,
            "success": bool(response.get("success")),
            "error": response.get("error"),
            "answer": answer,
            "answerHash": _stable_hash(answer) if answer else None,
            "durationMs": duration_ms,
            "mcpCallCount": len(mcp_logs),
            "pricingCallCount": len(pricing_logs),
            "kbCallCount": kb_call_count,
            "advisoryQuality": advisory_quality,
            "mcpLogs": mcp_logs,
            "pricingLogs": pricing_logs,
        }
        steps.append(step_record)

        with transcript_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {"role": "user", "turnId": turn.id, "content": turn.message},
                    ensure_ascii=False,
                )
                + "\n"
            )
            handle.write(
                json.dumps(
                    {
                        "role": "assistant",
                        "turnId": turn.id,
                        "success": step_record["success"],
                        "error": step_record["error"],
                        "answerHash": step_record["answerHash"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

        # Refresh state snapshot after each turn.
        state_resp = await _http_json(client, "GET", f"/api/projects/{project_id}/state")
        next_state = state_resp.get("projectState")
        if isinstance(next_state, dict):
            state = next_state

    # Final state summary
    final_missing_keys = _assert_required_state_keys(
        state, scenario.assertions.get("requireStateKeys", [])
    )

    state_summary = _summarize_state(state)

    waf_assert = scenario.assertions.get("requireWafChecklist")
    if isinstance(waf_assert, dict):
        min_items = waf_assert.get("minItems")
        if isinstance(min_items, int) and min_items > 0:
            waf_items = _get_waf_checklist_items(state)
            if len(waf_items) < min_items:
                raise AssertionError(
                    f"WAF checklist not populated: expected >= {min_items} items, got {len(waf_items)}"
                )

    require_kb_turn = scenario.assertions.get("requireKbCallsInTurn")
    if isinstance(require_kb_turn, dict):
        turn_id = str(require_kb_turn.get("turnId") or "")
        min_calls = require_kb_turn.get("minCalls")
        if turn_id and isinstance(min_calls, int) and min_calls > 0:
            matching = [s for s in steps if s.get("id") == turn_id]
            calls = int(matching[-1].get("kbCallCount") or 0) if matching else 0
            if calls < min_calls:
                raise AssertionError(
                    f"Expected at least {min_calls} KB tool calls during turn '{turn_id}', got {calls}."
                )

    # Aggregate advisory quality metrics
    advisory_scores = [
        step.get("advisoryQuality", {})
        for step in steps
        if step.get("advisoryQuality")
    ]
    
    if advisory_scores:
        avg_proactivity = sum(s.get("proactivity", 0) for s in advisory_scores) / len(advisory_scores)
        avg_correction = sum(s.get("correction", 0) for s in advisory_scores) / len(advisory_scores)
        avg_evidence = sum(s.get("evidence", 0) for s in advisory_scores) / len(advisory_scores)
        avg_clarity = sum(s.get("clarity", 0) for s in advisory_scores) / len(advisory_scores)
        avg_total = sum(s.get("total", 0) for s in advisory_scores) / len(advisory_scores)
        passed_count = sum(1 for s in advisory_scores if s.get("passed", False))
        
        advisory_summary = {
            "averages": {
                "proactivity": round(avg_proactivity, 2),
                "correction": round(avg_correction, 2),
                "evidence": round(avg_evidence, 2),
                "clarity": round(avg_clarity, 2),
                "total": round(avg_total, 2),
                "maxTotal": 8,
            },
            "turnsPassed": passed_count,
            "totalTurns": len(advisory_scores),
            "passRate": round(passed_count / len(advisory_scores), 2),
            "overallPassed": avg_total >= 4.0,  # Overall pass if avg >= 4/8
        }
    else:
        advisory_summary = None

    return {
        "projectId": project_id,
        "us1": {
            "missingRequiredKeys": missing_keys,
        },
        "final": {
            "missingRequiredKeys": final_missing_keys,
            "stateSummary": state_summary,
        },
        "advisoryQuality": advisory_summary,
        "steps": steps,
    }


async def _apply_human_adr_append(client: httpx.AsyncClient, project_id: str) -> None:
    state_resp = await _http_json(client, "GET", f"/api/projects/{project_id}/state")
    state = state_resp.get("projectState")
    if not isinstance(state, dict):
        return

    adrs = state.get("adrs")
    if not isinstance(adrs, list) or not adrs:
        return

    first = adrs[0]
    if not isinstance(first, dict) or "id" not in first:
        return

    adr_id = str(first["id"])
    await _http_json(
        client,
        "PATCH",
        f"/api/projects/{project_id}/adrs/{adr_id}/append",
        json={
            "adr_field": "decision",
            "append_text": "\n[HUMAN EDIT] The decision text was edited externally; do not overwrite this section.",
        },
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AAA E2E runner (backend-driven)")
    parser.add_argument("--scenario", required=True, help="Scenario id (e.g. scenario-a)")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--in-process", action="store_true", help="Run against in-process FastAPI app")
    mode.add_argument("--base-url", help="Run against a running backend (e.g. http://localhost:8000)")

    parser.add_argument("--update-goldens", action="store_true", help="Promote current output as golden")
    parser.add_argument("--timeout", type=float, default=120.0, help="HTTP timeout (seconds)")
    parser.add_argument(
        "--kb-root",
        default=None,
        help=(
            "Override KNOWLEDGE_BASES_ROOT for this run (useful for in-process E2E when KB indexes live outside the repo)."
        ),
    )

    return parser


def parse_config(args: argparse.Namespace) -> RunnerConfig:
    if args.in_process:
        mode: Literal["in-process", "remote"] = "in-process"
        base_url = "http://test"
    else:
        mode = "remote"
        base_url = str(args.base_url)

    return RunnerConfig(
        mode=mode,
        base_url=base_url,
        scenario_id=str(args.scenario),
        update_goldens=bool(args.update_goldens),
        timeout_s=float(args.timeout),
        kb_root=str(args.kb_root) if args.kb_root else None,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    config = parse_config(args)

    report = asyncio.run(run_scenario(config))

    normalized = normalize_report_for_golden(report)
    if report.get("goldenStatus") == "mismatch":
        print("E2E: GOLDEN MISMATCH")
        print(json.dumps(normalized, indent=2, ensure_ascii=False))
        return 2

    print(f"E2E: OK (goldenStatus={report.get('goldenStatus')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
