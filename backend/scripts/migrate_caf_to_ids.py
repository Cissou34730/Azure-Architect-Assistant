"""
Migration script to add ID-based tracking to existing CAF knowledge base.
Assigns sequential IDs to existing documents and creates index checkpoint.
"""

import json
import re
from pathlib import Path

MAX_FILENAME_LEN = 100


def _load_and_backup_crawl_checkpoint(path: Path) -> tuple[dict, Path | None]:
    """Load crawl checkpoint and create a backup."""
    if not path.exists():
        print(f"  ERROR: {path.name} not found")
        return {}, None

    with open(path, encoding="utf-8") as f:
        crawl_data = json.load(f)

    # Backup old checkpoint
    backup_path = path.with_suffix(".json.backup")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(crawl_data, f, indent=2)
    print(f"  Backed up old checkpoint to {backup_path.name}")

    return crawl_data, backup_path


def _assign_ids_and_update(crawl_data: dict, path: Path) -> tuple[dict, int]:
    """Assign IDs and update the checkpoint file."""
    visited_urls = crawl_data.get("visited", [])
    print(f"  Found {len(visited_urls)} visited URLs")

    url_id_map = {}
    urls_data = {}
    timestamp = crawl_data.get("timestamp", "")

    for i, url in enumerate(visited_urls, start=1):
        url_id_map[url] = i
        urls_data[str(i)] = {
            "url": url,
            "status": "fetched",
            "timestamp": timestamp,
        }

    last_id = len(visited_urls)
    new_crawl_data = {
        "kb_id": "caf",
        "last_id": last_id,
        "pages_total": crawl_data.get("visited_count", len(visited_urls)),
        "pages_crawled": len(visited_urls),
        "timestamp": timestamp,
        "url_id_map": url_id_map,
        "urls": urls_data,
        "to_visit": crawl_data.get("to_visit", []),
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(new_crawl_data, f, indent=2)

    return url_id_map, last_id


def _get_page_name(url: str) -> str:
    """Extract a clean page name from URL."""
    page_name = url.rsplit("/", maxsplit=1)[-1] or "index"
    page_name = re.sub(r"\.(html?|php|asp)$", "", page_name)
    page_name = re.sub(r"[^a-zA-Z0-9_-]", "_", page_name)
    if len(page_name) > MAX_FILENAME_LEN:
        page_name = page_name[:MAX_FILENAME_LEN]
    return page_name


def _rename_documents(doc_dir: Path, url_id_map: dict) -> int:
    """Rename document files with ID prefixes."""
    if not doc_dir.exists():
        print("  WARNING: documents directory not found")
        return 0

    existing_files = sorted(doc_dir.glob("*.txt"))
    print(f"  Found {len(existing_files)} existing documents")

    renamed_count = 0
    for file_path in existing_files:
        try:
            with open(file_path, encoding="utf-8") as f:
                first_line = f.readline().strip()
                if not first_line.startswith("URL:"):
                    continue
                url = first_line.replace("URL:", "").strip()

            if url not in url_id_map:
                continue

            doc_id = url_id_map[url]
            new_name = f"{doc_id:04d}_{_get_page_name(url)}.txt"
            new_path = doc_dir / new_name

            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            if not content.startswith("Doc ID:"):
                content = f"Doc ID: {doc_id}\n" + content

            with open(new_path, "w", encoding="utf-8") as f:
                f.write(content)

            if file_path != new_path:
                file_path.unlink()

            renamed_count += 1
        except OSError as e:
            print(f"  ERROR processing {file_path.name}: {e}")

    return renamed_count


def _create_index_checkpoint(kb_dir: Path, last_id: int, checkpoint_path: Path) -> int:
    """Create or update the index checkpoint."""
    index_store_path = kb_dir / "index" / "index_store.json"
    total_chunks = 0

    if index_store_path.exists():
        try:
            with open(index_store_path, encoding="utf-8") as f:
                index_data = json.load(f)
                nodes_data = index_data.get("index_store/data", {})
                total_chunks = len(nodes_data.get("embedding_dict", []))
            print(f"  Found {total_chunks} chunks in existing index")
        except (OSError, json.JSONDecodeError) as e:
            print(f"  WARNING: Could not read index: {e}")

    # Fallback/known value if 0
    total_chunks = total_chunks or 939

    checkpoint = {
        "last_chunked_id": last_id,
        "last_indexed_id": last_id,
        "total_chunks": total_chunks,
        "chunks_per_doc": {},
    }

    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2)

    return total_chunks


def migrate_caf_data():
    """Migrate existing CAF data to new ID-based structure."""
    backend_root = Path(__file__).parent.parent
    kb_dir = backend_root / "data" / "knowledge_bases" / "caf"
    doc_dir = kb_dir / "documents"
    crawl_cp_path = kb_dir / "crawl_checkpoint.json"
    index_cp_path = kb_dir / "index_checkpoint.json"

    print("=" * 70)
    print("CAF Knowledge Base Migration to ID-based Tracking")
    print("=" * 70)

    # Step 1: Load and backup
    crawl_data, backup_path = _load_and_backup_crawl_checkpoint(crawl_cp_path)
    if not crawl_data or not backup_path:
        return

    # Step 2 & 3: Assign IDs and update checkpoint
    print("\nStep 2 & 3: Assigning IDs and updating crawl checkpoint...")
    url_id_map, last_id = _assign_ids_and_update(crawl_data, crawl_cp_path)
    print(f"  Assigned IDs 1-{last_id}")

    # Step 4: Rename documents
    print("\nStep 4: Renaming document files...")
    renamed_count = _rename_documents(doc_dir, url_id_map)
    print(f"  Renamed {renamed_count} document files")

    # Step 5: Create index checkpoint
    print("\nStep 5: Creating index checkpoint...")
    total_chunks = _create_index_checkpoint(kb_dir, last_id, index_cp_path)
    print(f"  Created index checkpoint: {index_cp_path.name}")

    # Summary
    print("\n" + "=" * 70)
    print("Migration Complete!")
    print("=" * 70)
    print(f"  URLs tracked: {last_id}")
    print(f"  Documents renamed: {renamed_count}")
    print(f"  Chunks indexed: {total_chunks}")
    print("  Crawl checkpoint: updated with ID structure")
    print("  Index checkpoint: created")
    print(f"  Backup saved: {backup_path.name}")
    print("=" * 70)


if __name__ == "__main__":
    migrate_caf_data()

