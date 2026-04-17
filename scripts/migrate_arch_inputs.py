"""Backfill decomposed architecture inputs from legacy ProjectState blobs."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.shared.config.app_settings import get_app_settings

ARCHITECTURE_INPUT_KEYS = (
    "context",
    "nfrs",
    "applicationStructure",
    "dataCompliance",
    "technicalConstraints",
    "openQuestions",
)

ARCHITECTURE_COLUMN_MAP = {
    "context": "context_json",
    "nfrs": "nfrs_json",
    "applicationStructure": "application_structure_json",
    "dataCompliance": "data_compliance_json",
    "technicalConstraints": "technical_constraints_json",
    "openQuestions": "open_questions_json",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill project architecture inputs from ProjectState blobs."
    )
    parser.add_argument("--database", type=Path, default=None)
    parser.add_argument("--project-id", action="append", dest="project_ids", default=[])
    parser.add_argument(
        "--prune-blob",
        action="store_true",
        help="Remove migrated architecture-input keys from project_states.state after backfill.",
    )
    return parser.parse_args()


def _resolve_database_path(override: Path | None) -> Path:
    if override is not None:
        return override.resolve()

    settings = get_app_settings()
    if settings.projects_database is None:
        raise ValueError("PROJECTS_DATABASE must be configured")
    return settings.projects_database.resolve()


def _extract_architecture_inputs(state: dict[str, object]) -> dict[str, object]:
    return {key: state[key] for key in ARCHITECTURE_INPUT_KEYS if key in state}


def _strip_architecture_inputs(state: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in state.items() if key not in ARCHITECTURE_INPUT_KEYS}


def _build_query(project_ids: list[str]) -> tuple[str, tuple[str, ...]]:
    if not project_ids:
        return "SELECT project_id, state, updated_at FROM project_states ORDER BY project_id", ()

    placeholders = ", ".join("?" for _ in project_ids)
    query = (
        "SELECT project_id, state, updated_at FROM project_states "
        f"WHERE project_id IN ({placeholders}) ORDER BY project_id"
    )
    return query, tuple(project_ids)


def main() -> int:
    args = _parse_args()
    database_path = _resolve_database_path(args.database)
    query, params = _build_query(args.project_ids)

    migrated = 0
    skipped = 0

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, params).fetchall()

        for row in rows:
            state = json.loads(row["state"])
            if not isinstance(state, dict):
                skipped += 1
                continue

            architecture_inputs = _extract_architecture_inputs(state)
            if not architecture_inputs:
                skipped += 1
                continue

            payload = {
                column_name: json.dumps(architecture_inputs[state_key])
                for state_key, column_name in ARCHITECTURE_COLUMN_MAP.items()
                if state_key in architecture_inputs
            }
            payload.setdefault("updated_at", row["updated_at"])
            payload["project_id"] = row["project_id"]

            connection.execute(
                """
                INSERT INTO project_architecture_inputs (
                    project_id,
                    context_json,
                    nfrs_json,
                    application_structure_json,
                    data_compliance_json,
                    technical_constraints_json,
                    open_questions_json,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    context_json=excluded.context_json,
                    nfrs_json=excluded.nfrs_json,
                    application_structure_json=excluded.application_structure_json,
                    data_compliance_json=excluded.data_compliance_json,
                    technical_constraints_json=excluded.technical_constraints_json,
                    open_questions_json=excluded.open_questions_json,
                    updated_at=excluded.updated_at
                """,
                (
                    payload["project_id"],
                    payload.get("context_json"),
                    payload.get("nfrs_json"),
                    payload.get("application_structure_json"),
                    payload.get("data_compliance_json"),
                    payload.get("technical_constraints_json"),
                    payload.get("open_questions_json"),
                    payload["updated_at"],
                ),
            )

            if args.prune_blob:
                stripped_state = _strip_architecture_inputs(state)
                connection.execute(
                    "UPDATE project_states SET state = ? WHERE project_id = ?",
                    (json.dumps(stripped_state), row["project_id"]),
                )

            migrated += 1

        connection.commit()

    print(
        json.dumps(
            {
                "database": str(database_path),
                "migrated": migrated,
                "skipped": skipped,
                "prunedBlob": args.prune_blob,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
