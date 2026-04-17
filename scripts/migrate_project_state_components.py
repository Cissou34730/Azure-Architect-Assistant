"""Backfill decomposed ProjectState component families from legacy blobs."""

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

from app.core.app_settings import get_app_settings

from app.features.projects.infrastructure.project_state_components_repository import (
    PROJECT_STATE_COMPONENT_KEYS,
    extract_project_state_components,
    strip_project_state_components,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill decomposed ProjectState component families from ProjectState blobs."
    )
    parser.add_argument("--database", type=Path, default=None)
    parser.add_argument("--project-id", action="append", dest="project_ids", default=[])
    parser.add_argument(
        "--prune-blob",
        action="store_true",
        help="Remove migrated component keys from project_states.state after backfill.",
    )
    return parser.parse_args()


def _resolve_database_path(override: Path | None) -> Path:
    if override is not None:
        return override.resolve()

    settings = get_app_settings()
    if settings.projects_database is None:
        raise ValueError("PROJECTS_DATABASE must be configured")
    return settings.projects_database.resolve()


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

    migrated_rows = 0
    migrated_components = 0
    skipped = 0

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, params).fetchall()

        for row in rows:
            state = json.loads(row["state"])
            if not isinstance(state, dict):
                skipped += 1
                continue

            components = extract_project_state_components(state)
            if not components:
                skipped += 1
                continue

            for component_key in PROJECT_STATE_COMPONENT_KEYS:
                if component_key not in components:
                    continue
                connection.execute(
                    """
                    INSERT INTO project_state_components (
                        project_id,
                        component_key,
                        payload_json,
                        updated_at
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT(project_id, component_key) DO UPDATE SET
                        payload_json=excluded.payload_json,
                        updated_at=excluded.updated_at
                    """,
                    (
                        row["project_id"],
                        component_key,
                        json.dumps(components[component_key]),
                        row["updated_at"],
                    ),
                )
                migrated_components += 1

            if args.prune_blob:
                stripped_state = strip_project_state_components(state)
                connection.execute(
                    "UPDATE project_states SET state = ? WHERE project_id = ?",
                    (json.dumps(stripped_state), row["project_id"]),
                )

            migrated_rows += 1

        connection.commit()

    print(
        json.dumps(
            {
                "database": str(database_path),
                "migratedRows": migrated_rows,
                "migratedComponents": migrated_components,
                "skipped": skipped,
                "prunedBlob": args.prune_blob,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
