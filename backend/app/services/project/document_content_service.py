"""Service for retrieving stored project document content metadata."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProjectDocument


class DocumentContentService:
    """Encapsulates lookup and validation for document content downloads."""

    async def resolve_content(
        self,
        *,
        project_id: str,
        document_id: str,
        db: AsyncSession,
    ) -> dict[str, str | Path]:
        result = await db.execute(
            select(ProjectDocument).where(
                ProjectDocument.id == document_id,
                ProjectDocument.project_id == project_id,
            )
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")

        stored_path = (document.stored_path or "").strip()
        if stored_path == "":
            raise HTTPException(status_code=404, detail="Document content unavailable")

        resolved_path = Path(stored_path)
        if not resolved_path.is_file():
            raise HTTPException(status_code=404, detail="Document file missing")

        media_type = (document.mime_type or "").strip()
        if media_type in {"", "application/octet-stream"}:
            guessed_media_type, _ = mimetypes.guess_type(document.file_name or "")
            if guessed_media_type:
                media_type = guessed_media_type
        if media_type == "":
            media_type = "application/octet-stream"

        return {
            "path": resolved_path,
            "media_type": media_type,
            "file_name": document.file_name or "document",
        }

