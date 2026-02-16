import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models import Project, ProjectDocument
from app.projects_database import get_db


@pytest.fixture
async def async_client(test_db_session: AsyncSession):
    def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_upload_documents_returns_summary_and_persists_statuses(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = Project(id="proj-docs-1", name="Docs Project")
    test_db_session.add(project)
    await test_db_session.commit()

    def fake_extract_text(file_name: str, mime_type: str | None, content: bytes):
        if file_name == "bad.bin":
            return None, "unsupported format"
        return "ok text", None

    monkeypatch.setattr(
        "app.routers.project_management.services.document_service.extract_text_from_upload",
        fake_extract_text,
    )

    response = await async_client.post(
        f"/api/projects/{project.id}/documents",
        files=[
            ("documents", ("ok.txt", b"hello", "text/plain")),
            ("documents", ("bad.bin", b"\x00\x01", "application/octet-stream")),
        ],
    )
    assert response.status_code == 200
    payload = response.json()

    assert isinstance(payload.get("documents"), list)
    assert len(payload["documents"]) == 2

    upload_summary = payload.get("uploadSummary")
    assert isinstance(upload_summary, dict)
    assert upload_summary.get("attemptedDocuments") == 2
    assert upload_summary.get("parsedDocuments") == 1
    assert upload_summary.get("failedDocuments") == 1
    failures = upload_summary.get("failures")
    assert isinstance(failures, list)
    assert len(failures) == 1
    assert failures[0].get("documentId") is not None
    assert failures[0].get("fileName") == "bad.bin"
    assert failures[0].get("reason") == "unsupported format"

    persisted_docs = (
        await test_db_session.execute(
            select(ProjectDocument).where(ProjectDocument.project_id == project.id)
        )
    ).scalars().all()
    assert len(persisted_docs) == 2

    by_name = {doc.file_name: doc for doc in persisted_docs}
    assert by_name["ok.txt"].parse_status == "parsed"
    assert by_name["ok.txt"].analysis_status == "not_started"
    assert by_name["ok.txt"].parse_error in (None, "")

    assert by_name["bad.bin"].parse_status == "parse_failed"
    assert by_name["bad.bin"].analysis_status == "skipped"
    assert by_name["bad.bin"].parse_error == "unsupported format"

    state_response = await async_client.get(f"/api/projects/{project.id}/state")
    assert state_response.status_code == 200
    project_state = state_response.json().get("projectState", {})
    reference_documents = project_state.get("referenceDocuments")
    assert isinstance(reference_documents, list)
    assert len(reference_documents) == 2
    state_by_title = {
        str(item.get("title")): item
        for item in reference_documents
        if isinstance(item, dict)
    }
    content_url = state_by_title["ok.txt"].get("url")
    assert isinstance(content_url, str)
    content_response = await async_client.get(content_url)
    assert content_response.status_code == 200
    assert content_response.content == b"hello"
    assert state_by_title["ok.txt"].get("parseStatus") == "parsed"
    assert state_by_title["ok.txt"].get("analysisStatus") == "not_started"
    assert state_by_title["bad.bin"].get("parseStatus") == "parse_failed"
    assert state_by_title["bad.bin"].get("analysisStatus") == "skipped"
    assert state_by_title["bad.bin"].get("parseError") == "unsupported format"


@pytest.mark.asyncio
async def test_document_content_guesses_pdf_content_type_for_generic_upload(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = Project(id="proj-docs-pdf", name="PDF Project")
    test_db_session.add(project)
    await test_db_session.commit()

    def fake_extract_text(file_name: str, mime_type: str | None, content: bytes):
        return "pdf text", None

    monkeypatch.setattr(
        "app.routers.project_management.services.document_service.extract_text_from_upload",
        fake_extract_text,
    )

    response = await async_client.post(
        f"/api/projects/{project.id}/documents",
        files=[
            (
                "documents",
                (
                    "sample.pdf",
                    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF",
                    "application/octet-stream",
                ),
            ),
        ],
    )
    assert response.status_code == 200
    payload = response.json()
    documents = payload.get("documents")
    assert isinstance(documents, list)
    assert len(documents) == 1
    document_id = documents[0]["id"]

    content_response = await async_client.get(
        f"/api/projects/{project.id}/documents/{document_id}/content"
    )
    assert content_response.status_code == 200
    assert content_response.headers.get("content-type", "").startswith(
        "application/pdf"
    )
    content_disposition = content_response.headers.get("content-disposition", "")
    assert content_disposition.startswith("inline")
