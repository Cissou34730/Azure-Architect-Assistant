"""
Helpers for orchestrator document persistence.
"""

import logging
import re
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from llama_index.core import Document

from config import get_kb_storage_root

logger = logging.getLogger(__name__)


def save_documents_to_disk(kb_id: str, documents: List[Document]) -> None:
    """
    Save documents to disk with ID-based naming.

    Args:
        kb_id: Knowledge base identifier
        documents: List of documents to save
    """
    kb_root: Path = Path(get_kb_storage_root())
    doc_dir = kb_root / kb_id / "documents"
    doc_dir.mkdir(parents=True, exist_ok=True)

    for doc in documents:
        meta = doc.metadata or {}
        doc_id = meta.get("doc_id", 0)
        url = meta.get("url", "")

        # Extract page name from URL
        if url:
            parsed = urlparse(url)
            path = parsed.path.rstrip("/")
            page_name = path.split("/")[-1] if path else "index"
            page_name = re.sub(r"\.(html?|php|asp)$", "", page_name)
        else:
            page_name = "document"

        # Sanitize for Windows
        page_name = re.sub(r'[<>:"/\\|?*]', "_", page_name)
        page_name = re.sub(r"\s+", "_", page_name)
        page_name = page_name.strip("._")

        if not page_name or page_name == "_":
            page_name = "document"

        if len(page_name) > 100:
            page_name = page_name[:100]

        filename = f"{doc_id:04d}_{page_name}.md"
        doc_path = doc_dir / filename

        try:
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(f"# Doc ID: {doc_id}\n")
                f.write(f"# URL: {url}\n\n")
                f.write(doc.text or "")
            logger.debug(f"Saved document {doc_id} to {filename}")
        except Exception as exc:
            logger.error(f"Failed to save document {doc_id}: {exc}")
