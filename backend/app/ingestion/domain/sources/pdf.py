"""
PDF Source Handler
Handles PDF ingestion using PyMuPDF (free).
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from llama_index.core import Document
from llama_index.readers.file import PyMuPDFReader

from .handler_base import BaseSourceHandler

logger = logging.getLogger(__name__)


class PDFSourceHandler(BaseSourceHandler):
    """
    Handle PDF ingestion using free PyMuPDFReader.
    Supports local files and online PDFs.
    """

    def __init__(self, kb_id: str, job=None, state=None):
        super().__init__(kb_id, job=job, state=state)
        self.reader = PyMuPDFReader()
        logger.info(f"PDFSourceHandler initialized for KB: {kb_id}")

    def ingest(self, config: Dict[str, Any]) -> List[Document]:
        """
        Ingest PDFs from config.

        Args:
            config: Can contain 'local_paths', 'pdf_urls', or 'folder_path'

        Returns:
            List of Documents
        """
        all_docs = []
        metadata = config.get("metadata", {})

        # Local PDFs
        if "local_paths" in config:
            for path in config["local_paths"]:
                # State check removed - run to completion model

                docs = self.ingest_local_pdf(path, metadata)
                all_docs.extend(docs)

        # Online PDFs
        if "pdf_urls" in config:
            for url in config["pdf_urls"]:
                # State check removed - run to completion model

                docs = self.ingest_online_pdf(url, metadata)
                all_docs.extend(docs)

        # Folder of PDFs
        if "folder_path" in config:
            docs = self.ingest_pdf_folder(config["folder_path"])
            all_docs.extend(docs)

        return all_docs

    def ingest_local_pdf(
        self, file_path: str, metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Ingest local PDF file.

        Args:
            file_path: Path to PDF file
            metadata: Optional metadata

        Returns:
            List of LlamaIndex Documents
        """
        try:
            logger.info(f"Ingesting PDF: {file_path}")
            docs = self.reader.load_data(file_path=Path(file_path))

            # Enrich metadata
            for doc in docs:
                doc.metadata.update(
                    {
                        "source_type": "pdf",
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "kb_id": self.kb_id,
                        "date_ingested": datetime.now().isoformat(),
                        **(metadata or {}),
                    }
                )

            logger.info(f"Successfully ingested {len(docs)} documents from PDF")
            return docs

        except Exception as e:
            logger.error(f"Failed to ingest PDF {file_path}: {e}")
            return []

    def ingest_online_pdf(
        self, pdf_url: str, metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Ingest PDF from URL.

        Args:
            pdf_url: Direct URL to PDF file
            metadata: Optional metadata

        Returns:
            List of LlamaIndex Documents
        """
        import requests
        import tempfile

        try:
            logger.info(f"Downloading PDF: {pdf_url}")
            response = requests.get(pdf_url, timeout=60)
            response.raise_for_status()

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            # Ingest from temp file
            docs = self.ingest_local_pdf(tmp_path, metadata)

            # Update metadata with URL
            for doc in docs:
                doc.metadata["source_type"] = "pdf_online"
                doc.metadata["url"] = pdf_url
                doc.metadata.pop("file_path", None)

            # Clean up temp file
            os.unlink(tmp_path)

            return docs

        except Exception as e:
            logger.error(f"Failed to ingest PDF from {pdf_url}: {e}")
            return []

    def ingest_pdf_folder(
        self, folder_path: str, pattern: str = "*.pdf"
    ) -> List[Document]:
        """
        Ingest all PDFs from a folder.

        Args:
            folder_path: Path to folder containing PDFs
            pattern: File pattern (default: *.pdf)

        Returns:
            List of all documents from all PDFs
        """
        documents = []
        folder = Path(folder_path)

        pdf_files = list(folder.glob(pattern))
        logger.info(f"Found {len(pdf_files)} PDFs in {folder_path}")

        for pdf_file in pdf_files:
            docs = self.ingest_local_pdf(str(pdf_file))
            documents.extend(docs)

        return documents
