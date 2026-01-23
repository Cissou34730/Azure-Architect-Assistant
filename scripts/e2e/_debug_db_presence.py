from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate ADR + Mermaid persistence in SQLite DBs for a projectId"
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument(
        "--projects-db",
        default=str(Path("backend/data/projects.db")),
        help="Path to projects.db (can be outside repo)",
    )
    parser.add_argument(
        "--diagrams-db",
        default=str(Path("backend/data/diagrams.db")),
        help="Path to diagrams.db (can be outside repo)",
    )
    return parser.parse_args()


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _safe_json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return None


def _find_value_locations(
    *, conn: sqlite3.Connection, value: str, max_hits: int = 50
) -> list[dict[str, Any]]:
    tables = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    ]

    hits: list[dict[str, Any]] = []
    for table in tables:
        try:
            columns = conn.execute(f"PRAGMA table_info({table})").fetchall()
        except sqlite3.Error:
            continue

        for col in columns:
            col_name = str(col[1])
            col_type = str(col[2] or "")
            col_name_lower = col_name.lower()

            # Scan likely identifier columns, plus any column that looks project-related,
            # plus JSON/blob-like state columns (using LIKE) to avoid false negatives.
            is_id_like = col_name_lower in {"id", "project_id", "projectid"}
            is_project_like = "project" in col_name_lower
            is_state_like = col_name_lower in {"state", "payload", "data"}

            if not (is_id_like or is_project_like or is_state_like):
                continue

            try:
                if is_state_like:
                    count = conn.execute(
                        f"SELECT COUNT(*) FROM {table} WHERE {col_name} LIKE ?",
                        (f"%{value}%",),
                    ).fetchone()[0]
                else:
                    count = conn.execute(
                        f"SELECT COUNT(*) FROM {table} WHERE {col_name} = ?",
                        (value,),
                    ).fetchone()[0]
            except sqlite3.Error:
                continue

            if count:
                hits.append(
                    {
                        "table": table,
                        "column": col_name,
                        "type": col_type,
                        "count": int(count),
                    }
                )
                if len(hits) >= max_hits:
                    return hits

    return hits


def _query_project_state(*, projects_db: str, project_id: str) -> dict[str, Any]:
    if not Path(projects_db).exists():
        return {"exists": False, "error": f"projects db not found: {projects_db}"}

    with _connect(projects_db) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "project_states" not in tables:
            return {"exists": True, "error": "missing table project_states"}

        overview: dict[str, Any] = {}
        try:
            if "projects" in tables:
                overview["projects_total"] = int(
                    conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
                )
                # Best-effort sample columns
                overview["projects_latest"] = [
                    dict(r)
                    for r in conn.execute(
                        "SELECT id, name, created_at FROM projects ORDER BY created_at DESC LIMIT 5"
                    ).fetchall()
                ]

            overview["project_states_total"] = int(
                conn.execute("SELECT COUNT(*) FROM project_states").fetchone()[0]
            )
            overview["project_states_sample_ids"] = [
                r[0]
                for r in conn.execute(
                    "SELECT project_id FROM project_states ORDER BY updated_at DESC LIMIT 5"
                ).fetchall()
            ]
        except sqlite3.Error:
            overview = {}

        row = conn.execute(
            "SELECT project_id, state, updated_at FROM project_states WHERE project_id = ?",
            (project_id,),
        ).fetchone()

        if row is None:
            # Try to prove whether the project_id exists elsewhere in the DB.
            locations = _find_value_locations(conn=conn, value=project_id)
            return {
                "exists": True,
                "found": False,
                "id_locations": locations,
                "overview": overview,
            }

        state_text = str(row["state"])
        state = _safe_json_loads(state_text)
        adrs_count = None
        diagrams_count = None
        waf_items_count = None
        if isinstance(state, dict):
            adrs = state.get("adrs")
            adrs_count = len(adrs) if isinstance(adrs, list) else 0
            diagrams = state.get("diagrams")
            diagrams_count = len(diagrams) if isinstance(diagrams, list) else 0
            waf = state.get("wafChecklist") or state.get("waf_checklist")
            if isinstance(waf, dict):
                items = waf.get("items")
                waf_items_count = len(items) if isinstance(items, list) else 0

        return {
            "exists": True,
            "found": True,
            "updated_at": row["updated_at"],
            "adrs_count": adrs_count,
            "diagrams_refs_count": diagrams_count,
            "waf_items_count": waf_items_count,
            "overview": overview,
        }


def _query_diagrams(*, diagrams_db: str) -> dict[str, Any]:
    if not Path(diagrams_db).exists():
        return {"exists": False, "error": f"diagrams db not found: {diagrams_db}"}

    with _connect(diagrams_db) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "diagrams" not in tables:
            return {"exists": True, "error": "missing table diagrams"}

        overview: dict[str, Any] = {}
        try:
            overview["diagrams_total"] = int(
                conn.execute("SELECT COUNT(*) FROM diagrams").fetchone()[0]
            )
            overview["diagrams_latest"] = [
                dict(r)
                for r in conn.execute(
                    "SELECT id, diagram_type, created_at, LENGTH(source_code) AS source_len FROM diagrams ORDER BY created_at DESC LIMIT 5"
                ).fetchall()
            ]
        except sqlite3.Error:
            overview = {}

        # If diagram_sets exists and includes project_id, we can scope results to a single project.
        can_scope_by_project = False
        if "diagram_sets" in tables:
            cols = {
                row[1]
                for row in conn.execute("PRAGMA table_info(diagram_sets)").fetchall()
            }
            can_scope_by_project = "project_id" in cols

        return {
            "exists": True,
            "can_scope_by_project": can_scope_by_project,
            "overview": overview,
        }


def main() -> int:
    args = _parse_args()

    # Normalize relative paths from repo root if run there
    projects_db = str(Path(args.projects_db))
    diagrams_db = str(Path(args.diagrams_db))

    diagrams = _query_diagrams(diagrams_db=diagrams_db)

    # If we can scope diagrams by project, do so.
    if diagrams.get("exists") and diagrams.get("can_scope_by_project"):
        with _connect(diagrams_db) as conn:
            diagram_set_rows = conn.execute(
                "SELECT id FROM diagram_sets WHERE project_id = ? ORDER BY created_at DESC",
                (args.project_id,),
            ).fetchall()
            diagram_set_ids = [r["id"] for r in diagram_set_rows]

            if diagram_set_ids:
                placeholders = ",".join(["?"] * len(diagram_set_ids))
                total = conn.execute(
                    f"SELECT COUNT(*) AS c FROM diagrams WHERE diagram_set_id IN ({placeholders})",
                    tuple(diagram_set_ids),
                ).fetchone()["c"]

                counts = dict(
                    conn.execute(
                        f"SELECT diagram_type, COUNT(*) AS c FROM diagrams WHERE diagram_set_id IN ({placeholders}) GROUP BY diagram_type",
                        tuple(diagram_set_ids),
                    ).fetchall()
                )

                sample = conn.execute(
                    f"SELECT id, diagram_type, LENGTH(source_code) AS len, diagram_set_id FROM diagrams WHERE diagram_set_id IN ({placeholders}) ORDER BY created_at DESC LIMIT 5",
                    tuple(diagram_set_ids),
                ).fetchall()

                diagrams.update(
                    {
                        "diagram_set_count": len(diagram_set_ids),
                        "total_rows_for_project": int(total),
                        "counts_by_type_for_project": {
                            str(k): int(v) for k, v in counts.items()
                        },
                        "latest_rows_for_project": [dict(r) for r in sample],
                    }
                )
            else:
                diagrams.update(
                    {
                        "diagram_set_count": 0,
                        "total_rows_for_project": 0,
                        "counts_by_type_for_project": {},
                        "latest_rows_for_project": [],
                    }
                )

    # If we cannot scope by project, still try to locate the project id in common columns.
    if diagrams.get("exists") and not diagrams.get("can_scope_by_project"):
        try:
            with _connect(diagrams_db) as conn:
                diagrams["id_locations"] = _find_value_locations(
                    conn=conn, value=args.project_id
                )
        except sqlite3.Error as exc:
            diagrams["id_locations_error"] = str(exc)

    result = {
        "project_id": args.project_id,
        "projects_db": os.path.abspath(projects_db),
        "diagrams_db": os.path.abspath(diagrams_db),
        "project_state": _query_project_state(projects_db=projects_db, project_id=args.project_id),
        "diagrams": diagrams,
    }

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
