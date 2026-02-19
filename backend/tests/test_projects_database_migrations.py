from sqlalchemy import create_engine, text

from app.projects_database import _run_additive_schema_migrations


def _list_document_columns(connection) -> set[str]:
    rows = connection.execute(text("PRAGMA table_info(documents)")).fetchall()
    return {str(row[1]) for row in rows}


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

        columns = _list_document_columns(connection)
        assert "parse_status" in columns
        assert "analysis_status" in columns
        assert "parse_error" in columns
        assert "analyzed_at" in columns
        assert "last_analysis_run_id" in columns

