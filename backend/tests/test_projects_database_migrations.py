from sqlalchemy import create_engine, text

from app.shared.db.projects_database import _run_additive_schema_migrations


def _list_table_columns(connection, table_name: str) -> set[str]:
    rows = connection.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return {str(row[1]) for row in rows}


def _list_table_names(connection) -> set[str]:
    rows = connection.execute(text("SELECT name FROM sqlite_master WHERE type = 'table'"))
    return {str(row[0]) for row in rows}


def test_documents_additive_migration_is_idempotent() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE documents (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    raw_text TEXT NOT NULL,
                    uploaded_at TEXT NOT NULL
                )
                """
            )
        )

        _run_additive_schema_migrations(connection)
        _run_additive_schema_migrations(connection)

        columns = _list_table_columns(connection, "documents")
        assert "parse_status" in columns
        assert "analysis_status" in columns
        assert "parse_error" in columns
        assert "analyzed_at" in columns
        assert "last_analysis_run_id" in columns


def test_pending_changes_additive_migration_is_idempotent() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    text_requirements TEXT,
                    created_at TEXT NOT NULL,
                    deleted_at TEXT
                )
                """
            )
        )

        _run_additive_schema_migrations(connection)
        _run_additive_schema_migrations(connection)

        table_names = _list_table_names(connection)
        assert "pending_change_sets" in table_names
        assert "artifact_drafts" in table_names

        change_set_columns = _list_table_columns(connection, "pending_change_sets")
        assert {
            "id",
            "project_id",
            "stage",
            "status",
            "created_at",
            "source_message_id",
            "superseded_by",
            "bundle_summary",
            "proposed_patch_json",
            "citations_json",
            "reviewed_at",
            "review_reason",
            "rejection_reason",
            "waf_delta_json",
            "mindmap_delta_json",
        }.issubset(change_set_columns)

        draft_columns = _list_table_columns(connection, "artifact_drafts")
        assert {
            "id",
            "change_set_id",
            "artifact_type",
            "artifact_id",
            "content_json",
            "citations_json",
            "created_at",
        }.issubset(draft_columns)
