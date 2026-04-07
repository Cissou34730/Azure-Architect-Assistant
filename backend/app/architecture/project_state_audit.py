"""Helpers for auditing legacy ProjectState JSON blobs."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.shared.config.app_settings import get_app_settings


@dataclass(frozen=True)
class ProjectStateRow:
    """Minimal row projection used for ProjectState audits."""

    project_id: str
    state: str | None


@dataclass(frozen=True)
class ProjectStateAuditReport:
    """Aggregated view of top-level ProjectState blob usage."""

    total_rows: int
    object_rows: int
    empty_row_ids: tuple[str, ...]
    malformed_row_ids: tuple[str, ...]
    non_object_row_ids: tuple[str, ...]
    key_occurrences: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the report."""
        return asdict(self)


def resolve_projects_database_path(db_path: str | Path | None = None) -> Path:
    """Resolve the configured projects DB path via AppSettings unless overridden."""
    resolved = Path(db_path) if db_path is not None else get_app_settings().projects_database
    if resolved is None:
        raise ValueError("projects database path is not configured")
    return resolved.resolve()


def load_project_state_rows(database_path: Path) -> list[ProjectStateRow]:
    """Load project_id/state pairs from the projects database."""
    if not database_path.exists():
        raise FileNotFoundError(f"Projects database not found: {database_path}")

    try:
        with sqlite3.connect(database_path) as connection:
            rows = connection.execute(
                "SELECT project_id, state FROM project_states ORDER BY project_id"
            ).fetchall()
    except sqlite3.Error as exc:
        raise RuntimeError(
            f"Unable to query project_states from {database_path}: {exc}"
        ) from exc

    return [ProjectStateRow(project_id=str(project_id), state=state) for project_id, state in rows]


def audit_project_state_rows(rows: Iterable[ProjectStateRow]) -> ProjectStateAuditReport:
    """Count top-level keys and identify rows that cannot be inventoried safely."""
    key_counter: Counter[str] = Counter()
    empty_row_ids: list[str] = []
    malformed_row_ids: list[str] = []
    non_object_row_ids: list[str] = []
    total_rows = 0
    object_rows = 0

    for row in rows:
        total_rows += 1
        raw_state = row.state
        if raw_state is None or not raw_state.strip():
            empty_row_ids.append(row.project_id)
            continue

        try:
            payload = json.loads(raw_state)
        except json.JSONDecodeError:
            malformed_row_ids.append(row.project_id)
            continue

        if not isinstance(payload, dict):
            non_object_row_ids.append(row.project_id)
            continue

        object_rows += 1
        key_counter.update(str(key) for key in payload)

    return ProjectStateAuditReport(
        total_rows=total_rows,
        object_rows=object_rows,
        empty_row_ids=tuple(empty_row_ids),
        malformed_row_ids=tuple(malformed_row_ids),
        non_object_row_ids=tuple(non_object_row_ids),
        key_occurrences=dict(sorted(key_counter.items())),
    )


def render_text_summary(report: ProjectStateAuditReport) -> str:
    """Render a concise human-readable audit summary."""
    lines = [
        "ProjectState audit summary",
        f"Rows scanned: {report.total_rows}",
        f"JSON objects: {report.object_rows}",
        f"Empty rows: {len(report.empty_row_ids)}",
        f"Malformed rows: {len(report.malformed_row_ids)}",
        f"Non-object rows: {len(report.non_object_row_ids)}",
    ]
    if report.key_occurrences:
        lines.append("Top-level key counts:")
        lines.extend(
            f"- {key}: {count}" for key, count in report.key_occurrences.items()
        )
    return "\n".join(lines)


def render_markdown_inventory(report: ProjectStateAuditReport) -> str:
    """Render the audit report as markdown suitable for docs or issue comments."""
    lines = [
        "# ProjectState Inventory",
        "",
        "## Summary",
        "",
        f"- Rows scanned: {report.total_rows}",
        f"- JSON object rows: {report.object_rows}",
        f"- Empty rows: {len(report.empty_row_ids)}",
        f"- Malformed rows: {len(report.malformed_row_ids)}",
        f"- Non-object rows: {len(report.non_object_row_ids)}",
        "",
        "## Top-level keys",
        "",
    ]

    if report.key_occurrences:
        lines.extend([
            "| Key | Count |",
            "| --- | ---: |",
        ])
        lines.extend(
            f"| {key} | {count} |" for key, count in report.key_occurrences.items()
        )
    else:
        lines.append("No top-level JSON object keys were found.")

    lines.extend(_render_row_section("Empty rows", report.empty_row_ids))
    lines.extend(_render_row_section("Malformed rows", report.malformed_row_ids))
    lines.extend(_render_row_section("Non-object rows", report.non_object_row_ids))
    return "\n".join(lines)


def _render_row_section(title: str, row_ids: tuple[str, ...]) -> list[str]:
    lines = ["", f"## {title}", ""]
    if row_ids:
        lines.extend(f"- {row_id}" for row_id in row_ids)
    else:
        lines.append("- None")
    return lines


def build_cli_parser() -> argparse.ArgumentParser:
    """Create the CLI parser used by the repo script wrapper."""
    parser = argparse.ArgumentParser(
        description="Audit top-level keys and malformed rows in ProjectState JSON blobs."
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Optional override for the projects database path.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Summary output format for stdout.",
    )
    parser.add_argument(
        "--emit-markdown",
        action="store_true",
        help="Append a markdown inventory to stdout after the summary.",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=None,
        help="Optional path to write the markdown inventory to.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point used by scripts/audit_project_state_blob.py."""
    parser = build_cli_parser()
    args = parser.parse_args(argv)

    report = audit_project_state_rows(
        load_project_state_rows(resolve_projects_database_path(args.db_path))
    )

    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(render_text_summary(report))

    markdown = render_markdown_inventory(report)
    if args.emit_markdown:
        print()
        print(markdown)

    if args.markdown_output is not None:
        args.markdown_output.write_text(markdown + "\n", encoding="utf-8")

    return 0


__all__ = [
    "ProjectStateAuditReport",
    "ProjectStateRow",
    "audit_project_state_rows",
    "build_cli_parser",
    "load_project_state_rows",
    "main",
    "render_markdown_inventory",
    "render_text_summary",
    "resolve_projects_database_path",
]
