"""Service for retrieving stored project document content metadata."""

from __future__ import annotations

import html
import mimetypes
import textwrap
from pathlib import Path
from typing import Literal, TypedDict

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProjectDocument
from app.shared.config.app_settings import get_app_settings


class DocumentFilePayload(TypedDict):
    kind: Literal["file"]
    path: Path
    media_type: str
    file_name: str


class DocumentInlinePayload(TypedDict):
    kind: Literal["inline"]
    content: str
    media_type: str
    file_name: str


DocumentContentPayload = DocumentFilePayload | DocumentInlinePayload


class DocumentContentService:
    """Encapsulates lookup and validation for document content downloads."""

    async def resolve_content(
        self,
        *,
        project_id: str,
        document_id: str,
        db: AsyncSession,
    ) -> DocumentContentPayload:
        result = await db.execute(
            select(ProjectDocument).where(
                ProjectDocument.id == document_id,
                ProjectDocument.project_id == project_id,
            )
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")

        resolved_path = self._resolve_file_path(
            project_id=project_id,
            document_id=document_id,
            document=document,
        )
        if resolved_path is None:
            rebuilt_pdf_path = self._rebuild_pdf_if_possible(
                project_id=project_id,
                document_id=document_id,
                document=document,
            )
            if rebuilt_pdf_path is not None:
                resolved_path = rebuilt_pdf_path
            else:
                inline_preview = self._build_inline_preview(document)
                if inline_preview is None:
                    raise HTTPException(status_code=404, detail="Document file missing")
                return inline_preview

        media_type = (document.mime_type or "").strip()
        if media_type in {"", "application/octet-stream"}:
            guessed_media_type, _ = mimetypes.guess_type(document.file_name or "")
            if guessed_media_type:
                media_type = guessed_media_type
        if media_type == "":
            media_type = "application/octet-stream"

        return {
            "kind": "file",
            "path": resolved_path,
            "media_type": media_type,
            "file_name": document.file_name or "document",
        }

    def _resolve_file_path(
        self,
        *,
        project_id: str,
        document_id: str,
        document: ProjectDocument,
    ) -> Path | None:
        candidates: list[Path] = []
        stored_path = (document.stored_path or "").strip()
        if stored_path != "":
            candidates.append(Path(stored_path))
            fallback_path = self._fallback_path(stored_path)
            if fallback_path is not None:
                candidates.append(fallback_path)

        expected_current_path = self._build_canonical_path(
            project_id=project_id,
            document_id=document_id,
            file_name=document.file_name or "document",
        )
        candidates.append(expected_current_path)

        for root in self._historical_roots():
            candidates.append(root / project_id / expected_current_path.name)

        seen: set[Path] = set()
        for candidate in candidates:
            normalized = candidate.resolve(strict=False)
            if normalized in seen:
                continue
            seen.add(normalized)
            if candidate.is_file():
                return candidate

        discovered = self._search_storage_roots(document_id=document_id, file_name=document.file_name or "document")
        return discovered

    @staticmethod
    def _fallback_path(stored_path: str) -> Path | None:
        """Try resolving a stale absolute path relative to the configured documents root.

        Looks for a ``project_documents`` segment in the path and rebuilds
        the suffix under ``get_app_settings().project_documents_root``.
        """
        parts = Path(stored_path).parts
        marker = "project_documents"
        try:
            idx = parts.index(marker)
        except ValueError:
            return None
        relative_suffix = Path(*parts[idx + 1 :])
        return get_app_settings().project_documents_root / relative_suffix

    @staticmethod
    def _build_canonical_path(*, project_id: str, document_id: str, file_name: str) -> Path:
        safe_file_name = Path(file_name).name or "document"
        return get_app_settings().project_documents_root / project_id / f"{document_id}_{safe_file_name}"

    @staticmethod
    def _historical_roots() -> list[Path]:
        settings = get_app_settings()
        current_root = settings.project_documents_root
        backend_root = settings.data_root.parent
        legacy_root = backend_root / "app" / "data" / "project_documents"
        roots = [current_root, legacy_root]
        unique_roots: list[Path] = []
        seen: set[Path] = set()
        for root in roots:
            normalized = root.resolve(strict=False)
            if normalized in seen:
                continue
            seen.add(normalized)
            unique_roots.append(root)
        return unique_roots

    def _search_storage_roots(self, *, document_id: str, file_name: str) -> Path | None:
        safe_file_name = Path(file_name).name or "document"
        exact_name = f"{document_id}_{safe_file_name}"
        for root in self._historical_roots():
            if not root.exists():
                continue
            direct_matches = list(root.rglob(exact_name))
            direct_files = [match for match in direct_matches if match.is_file()]
            if direct_files:
                return direct_files[0]

        for root in self._historical_roots():
            if not root.exists():
                continue
            id_matches = list(root.rglob(f"{document_id}_*"))
            id_files = [match for match in id_matches if match.is_file()]
            if id_files:
                return id_files[0]

        for root in self._historical_roots():
            if not root.exists():
                continue
            name_matches = list(root.rglob(safe_file_name))
            name_files = [match for match in name_matches if match.is_file()]
            if len(name_files) == 1:
                return name_files[0]
        return None

    def _rebuild_pdf_if_possible(
        self,
        *,
        project_id: str,
        document_id: str,
        document: ProjectDocument,
    ) -> Path | None:
        if not self._is_pdf_document(document):
            return None
        raw_text = (document.raw_text or "").strip()
        if raw_text == "":
            return None

        target_path = self._build_canonical_path(
            project_id=project_id,
            document_id=document_id,
            file_name=document.file_name or "document.pdf",
        )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_text_pdf(
            target_path=target_path,
            title=document.file_name or "document.pdf",
            body=raw_text,
        )
        return target_path

    @staticmethod
    def _is_pdf_document(document: ProjectDocument) -> bool:
        mime_type = (document.mime_type or "").lower()
        file_name = (document.file_name or "").lower()
        return mime_type == "application/pdf" or file_name.endswith(".pdf")

    @staticmethod
    def _write_text_pdf(*, target_path: Path, title: str, body: str) -> None:
        import fitz

        pdf = fitz.open()
        page = pdf.new_page(width=595, height=842)
        y = 48.0
        line_height = 14.0
        max_y = 794.0

        def write_line(text: str, *, font_size: float = 11.0) -> None:
            nonlocal page, y
            if y > max_y:
                page = pdf.new_page(width=595, height=842)
                y = 48.0
            page.insert_text((48.0, y), text, fontsize=font_size, fontname="helv")
            y += line_height if font_size <= 11.0 else 18.0

        write_line(title, font_size=14.0)
        write_line("Recovered from persisted extracted text because the original uploaded PDF path was unavailable.")
        write_line("")
        for raw_line in body.splitlines() or [body]:
            wrapped_lines = textwrap.wrap(raw_line, width=90) or [""]
            for wrapped_line in wrapped_lines:
                write_line(wrapped_line)

        pdf.save(target_path)
        pdf.close()

    @staticmethod
    def _build_inline_preview(document: ProjectDocument) -> DocumentInlinePayload | None:
        raw_text = (document.raw_text or "").strip()
        if raw_text == "":
            return None

        escaped_title = html.escape(document.file_name or "document")
        escaped_body = html.escape(raw_text)
        content = (
            "<!doctype html>"
            "<html><head><meta charset=\"utf-8\">"
            f"<title>{escaped_title}</title>"
            "<style>body{font-family:Segoe UI,Arial,sans-serif;margin:0;padding:24px;line-height:1.5;color:#1f2937;}"
            ".banner{margin-bottom:16px;padding:12px 14px;border:1px solid #f59e0b;background:#fffbeb;color:#92400e;border-radius:8px;}"
            "h1{margin:0 0 12px;font-size:20px;}pre{white-space:pre-wrap;word-break:break-word;"
            "background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px;padding:16px;}</style></head><body>"
            f"<div class=\"banner\">Original uploaded file is unavailable. Showing persisted extracted text preview for {escaped_title}.</div>"
            f"<h1>{escaped_title}</h1><pre>{escaped_body}</pre></body></html>"
        )
        return {
            "kind": "inline",
            "content": content,
            "media_type": "text/html",
            "file_name": document.file_name or "document",
        }

