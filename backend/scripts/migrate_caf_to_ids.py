"""
Migration script to add ID-based tracking to existing CAF knowledge base.
Assigns sequential IDs to existing documents and creates index checkpoint.
"""

import json
import re
from pathlib import Path


def migrate_caf_data():
    """Migrate existing CAF data to new ID-based structure."""

    # Paths
    backend_root = Path(__file__).parent.parent
    kb_dir = backend_root / "data" / "knowledge_bases" / "caf"
    doc_dir = kb_dir / "documents"
    crawl_checkpoint_path = kb_dir / "crawl_checkpoint.json"
    index_checkpoint_path = kb_dir / "index_checkpoint.json"

    print("=" * 70)
    print("CAF Knowledge Base Migration to ID-based Tracking")
    print("=" * 70)

    # Step 1: Load existing crawl checkpoint
    print("\nStep 1: Loading crawl checkpoint...")
    if not crawl_checkpoint_path.exists():
        print("  ERROR: crawl_checkpoint.json not found")
        return

    with open(crawl_checkpoint_path, "r", encoding="utf-8") as f:
        crawl_data = json.load(f)

    visited_urls = crawl_data.get("visited", [])
    print(f"  Found {len(visited_urls)} visited URLs")

    # Step 2: Assign sequential IDs to URLs
    print("\nStep 2: Assigning sequential IDs to URLs...")
    url_id_map = {}
    urls_data = {}

    for i, url in enumerate(visited_urls, start=1):
        url_id_map[url] = i
        urls_data[str(i)] = {
            "url": url,
            "status": "fetched",
            "timestamp": crawl_data.get("timestamp", ""),
        }

    last_id = len(visited_urls)
    print(f"  Assigned IDs 1-{last_id}")

    # Step 3: Update crawl checkpoint with ID structure
    print("\nStep 3: Updating crawl checkpoint...")
    new_crawl_data = {
        "kb_id": "caf",
        "last_id": last_id,
        "pages_total": crawl_data.get("visited_count", len(visited_urls)),
        "pages_crawled": len(visited_urls),
        "timestamp": crawl_data.get("timestamp", ""),
        "url_id_map": url_id_map,
        "urls": urls_data,
        "to_visit": crawl_data.get("to_visit", []),
    }

    # Backup old checkpoint
    backup_path = crawl_checkpoint_path.with_suffix(".json.backup")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(crawl_data, f, indent=2)
    print(f"  Backed up old checkpoint to {backup_path.name}")

    # Write new checkpoint
    with open(crawl_checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(new_crawl_data, f, indent=2)
    print("  Updated crawl checkpoint with ID structure")

    # Step 4: Rename document files with ID prefix
    print("\nStep 4: Renaming document files...")
    if not doc_dir.exists():
        print("  WARNING: documents directory not found")
        renamed_count = 0
    else:
        # Get all existing .txt files
        existing_files = sorted(doc_dir.glob("*.txt"))
        print(f"  Found {len(existing_files)} existing documents")

        # Map files to URLs by reading the URL from file content
        file_to_url = {}
        for file_path in existing_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line.startswith("URL:"):
                        url = first_line.replace("URL:", "").strip()
                        file_to_url[file_path] = url
            except Exception as e:
                print(f"  WARNING: Could not read URL from {file_path.name}: {e}")

        print(f"  Matched {len(file_to_url)} files to URLs")

        # Rename files with ID prefix
        renamed_count = 0
        for file_path, url in file_to_url.items():
            if url in url_id_map:
                doc_id = url_id_map[url]

                # Extract page name from URL
                page_name = url.split("/")[-1] or "index"
                page_name = re.sub(r"\.(html?|php|asp)$", "", page_name)
                page_name = re.sub(r"[^a-zA-Z0-9_-]", "_", page_name)
                if len(page_name) > 100:
                    page_name = page_name[:100]

                # New filename: {id:04d}_{page-name}.txt
                new_name = f"{doc_id:04d}_{page_name}.txt"
                new_path = doc_dir / new_name

                # Update file content with doc_id
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Insert Doc ID at the beginning
                    if not content.startswith("Doc ID:"):
                        content = f"Doc ID: {doc_id}\n" + content

                    with open(new_path, "w", encoding="utf-8") as f:
                        f.write(content)

                    # Delete old file if different
                    if file_path != new_path:
                        file_path.unlink()

                    renamed_count += 1
                except Exception as e:
                    print(f"  ERROR renaming {file_path.name} to {new_name}: {e}")

        print(f"  Renamed {renamed_count} document files")

    # Step 5: Create index checkpoint
    print("\nStep 5: Creating index checkpoint...")

    # Count chunks from existing index if available
    index_store_path = kb_dir / "index" / "index_store.json"
    total_chunks = 0

    if index_store_path.exists():
        try:
            with open(index_store_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)
                # Count nodes in index
                if "index_store/data" in index_data:
                    nodes_dict = index_data["index_store/data"]
                    if "embedding_dict" in nodes_dict:
                        total_chunks = len(nodes_dict["embedding_dict"])
            print(f"  Found {total_chunks} chunks in existing index")
        except Exception as e:
            print(f"  WARNING: Could not read index: {e}")

    index_checkpoint = {
        "last_chunked_id": last_id,
        "last_indexed_id": last_id,
        "total_chunks": total_chunks or 939,  # Fallback to known value
        "chunks_per_doc": {},
    }

    with open(index_checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(index_checkpoint, f, indent=2)
    print(f"  Created index checkpoint: {index_checkpoint_path.name}")

    # Summary
    print("\n" + "=" * 70)
    print("Migration Complete!")
    print("=" * 70)
    print(f"  URLs tracked: {last_id}")
    print(f"  Documents renamed: {renamed_count}")
    print(f"  Chunks indexed: {index_checkpoint['total_chunks']}")
    print("  Crawl checkpoint: updated with ID structure")
    print("  Index checkpoint: created")
    print(f"  Backup saved: {backup_path.name}")
    print("=" * 70)


if __name__ == "__main__":
    migrate_caf_data()
