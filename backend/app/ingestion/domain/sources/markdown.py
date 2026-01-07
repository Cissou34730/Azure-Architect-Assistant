"""
Markdown Source Handler
Handles markdown file ingestion using SimpleDirectoryReader.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from llama_index.core import Document, SimpleDirectoryReader

from .handler_base import BaseSourceHandler

logger = logging.getLogger(__name__)


class MarkdownSourceHandler(BaseSourceHandler):
    """
    Handle Markdown file ingestion using SimpleDirectoryReader.
    Preserves markdown structure and hierarchy.
    """

    def __init__(self, kb_id: str, job=None, state=None):
        super().__init__(kb_id, job=job, state=state)
        logger.info(f"MarkdownSourceHandler initialized for KB: {kb_id}")

    def ingest(self, config: Dict[str, Any]) -> List[Document]:
        """
        Ingest markdown files from config.

        Args:
            config: Must contain 'folder_path'

        Returns:
            List of Documents
        """
        folder_path = config.get("folder_path")
        if not folder_path:
            raise ValueError("Markdown config requires 'folder_path'")

        metadata = config.get("metadata", {})
        return self.ingest_folder(folder_path, metadata)

    def ingest_folder(
        self, folder_path: str, metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Ingest all Markdown files from a folder.

        Args:
            folder_path: Path to folder containing .md files
            metadata: Optional metadata

        Returns:
            List of LlamaIndex Documents
        """
        try:
            logger.info(f"Ingesting Markdown folder: {folder_path}")

            reader = SimpleDirectoryReader(
                input_dir=folder_path, required_exts=[".md"], recursive=True
            )
            docs = reader.load_data()

            # State check removed - run to completion model

            # Enrich metadata
            for doc in docs:
                file_path = doc.metadata.get("file_path", "")
                doc.metadata.update(
                    {
                        "source_type": "markdown",
                        "folder_path": folder_path,
                        "kb_id": self.kb_id,
                        "date_ingested": datetime.now().isoformat(),
                        "hierarchy": self._extract_hierarchy(file_path, folder_path),
                        **(metadata or {}),
                    }
                )

            logger.info(f"Successfully ingested {len(docs)} Markdown documents")
            return docs

        except Exception as e:
            logger.error(f"Failed to ingest Markdown folder {folder_path}: {e}")
            return []

    def ingest_file(
        self, file_path: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Document]:
        """
        Ingest single Markdown file.

        Args:
            file_path: Path to .md file
            metadata: Optional metadata

        Returns:
            LlamaIndex Document or None
        """
        try:
            logger.info(f"Ingesting Markdown file: {file_path}")

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            doc = Document(
                text=content,
                metadata={
                    "source_type": "markdown",
                    "file_path": file_path,
                    "file_name": os.path.basename(file_path),
                    "kb_id": self.kb_id,
                    "date_ingested": datetime.now().isoformat(),
                    **(metadata or {}),
                },
            )

            return doc

        except Exception as e:
            logger.error(f"Failed to ingest Markdown file {file_path}: {e}")
            return None

    def _extract_hierarchy(self, file_path: str, base_path: str) -> Dict[str, Any]:
        """Extract folder hierarchy from file path"""
        try:
            rel_path = Path(file_path).relative_to(base_path)
            parts = rel_path.parts

            return {
                "depth": len(parts) - 1,
                "path_components": list(parts),
                "category": parts[0] if len(parts) > 1 else "root",
            }
        except:
            return {"depth": 0, "path_components": [], "category": "root"}
