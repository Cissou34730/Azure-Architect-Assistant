#!/usr/bin/env python
"""Import Azure WAF pillar checklists from Microsoft Learn via MCP."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin


def _ensure_backend_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    backend_path = repo_root / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))


_ensure_backend_on_path()

from app.agents_system.checklists.default_templates import (  # noqa: E402
    WAF_PILLAR_TEMPLATES,
)
from app.core.app_settings import get_settings  # noqa: E402
from app.services.mcp.learn_mcp_client import MicrosoftLearnMCPClient  # noqa: E402
from app.services.mcp.operations.learn_operations import fetch_documentation  # noqa: E402

_CHECKLIST_ROW_PREFIX = "|"
_CODE_LINK_RE = re.compile(r"\[([A-Z]{2}:\d{2})\]\(([^)]+)\)")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_WHITESPACE_RE = re.compile(r"\s+")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Azure WAF pillar checklists from Microsoft Learn MCP and write JSON templates."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("backend/config/checklists"),
        help="Directory to write checklist templates.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary only without writing files.",
    )
    return parser.parse_args()


def _normalize_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value.replace("\\*", "*")).strip()


def _extract_title_and_description(recommendation_column: str) -> tuple[str, str]:
    cleaned = _normalize_text(recommendation_column)
    title_match = _BOLD_RE.search(cleaned)
    if title_match:
        raw_title = _normalize_text(title_match.group(1)).rstrip(".")
        without_bold = cleaned.replace(title_match.group(0), "", 1).strip()
        description = without_bold.lstrip(". ").strip()
        return raw_title if raw_title else cleaned, description if description else cleaned
    return cleaned, cleaned


def _parse_markdown_rows(markdown: str, source_url: str, pillar: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line.startswith(_CHECKLIST_ROW_PREFIX):
            continue
        if "Recommendation" in line or "---" in line:
            continue

        parts = [segment.strip() for segment in line.strip("|").split("|")]
        if len(parts) < 3:
            continue

        code_column = parts[1]
        recommendation_column = parts[2]
        link_match = _CODE_LINK_RE.search(code_column)
        if not link_match:
            continue

        code = link_match.group(1).upper()
        href = link_match.group(2)
        item_id = code.lower().replace(":", "-")
        if item_id in seen_ids:
            continue

        title, description = _extract_title_and_description(recommendation_column)
        recommendation_text = _normalize_text(recommendation_column.replace("**", ""))
        item_url = urljoin(source_url, href)

        items.append(
            {
                "id": item_id,
                "title": title,
                "description": description,
                "pillar": pillar,
                "severity": "medium",
                "guidance": {
                    "code": code,
                    "recommendation": recommendation_text,
                    "learn_url": item_url,
                },
                "item_metadata": {
                    "code": code,
                    "source_url": item_url,
                },
            }
        )
        seen_ids.add(item_id)

    return items


def _build_template_payload(
    slug: str,
    title: str,
    source_url: str,
    pillar: str,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    version = now.date().isoformat()
    return {
        "slug": slug,
        "title": title,
        "description": f"Azure Well-Architected Framework checklist for the {pillar} pillar.",
        "version": version,
        "source": "microsoft-learn",
        "source_url": source_url,
        "source_version": version,
        "source_license": "Microsoft Learn Terms of Use",
        "fetched_at": timestamp,
        "content": {"items": items},
    }


async def _fetch_templates() -> list[dict[str, Any]]:
    settings = get_settings()
    config = settings.get_mcp_server_config("microsoft_learn")
    client = MicrosoftLearnMCPClient(config)
    await client.initialize()
    try:
        templates: list[dict[str, Any]] = []
        for definition in WAF_PILLAR_TEMPLATES:
            document = await fetch_documentation(client, definition.source_url)
            markdown = str(document.get("content", ""))
            items = _parse_markdown_rows(markdown, definition.source_url, definition.pillar)
            templates.append(
                _build_template_payload(
                    slug=definition.slug,
                    title=definition.title,
                    source_url=definition.source_url,
                    pillar=definition.pillar,
                    items=items,
                )
            )
        return templates
    finally:
        await client.close()


def _write_templates(output_dir: Path, templates: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for template in templates:
        slug = str(template.get("slug", "")).strip()
        if not slug:
            continue
        file_path = output_dir / f"{slug}.json"
        file_path.write_text(json.dumps(template, indent=2), encoding="utf-8")


async def _main() -> int:
    args = _parse_args()
    templates = await _fetch_templates()

    summary = [
        {
            "slug": template["slug"],
            "items": len(template.get("content", {}).get("items", [])),
            "source_url": template["source_url"],
        }
        for template in templates
    ]
    print(json.dumps({"templates": summary}, indent=2))

    if not args.dry_run:
        _write_templates(args.output_dir, templates)
        print(f"Wrote {len(templates)} templates to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
