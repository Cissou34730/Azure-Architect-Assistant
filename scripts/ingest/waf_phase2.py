"""
WAF Ingestion - Phase 2: Chunking, Embeddings, Indexing
Processes APPROVED documents and builds the vector index.
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend/src/rag to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(project_root, 'backend', 'src', 'rag'))

from indexer import WAFIndexBuilder

def main():
    """Run Phase 2: Build index from approved documents."""
    
    print("="*70)
    print("WAF INGESTION - PHASE 2")
    print("Chunk -> Embed -> Index (APPROVED documents only)")
    print("="*70 + "\n")
    
    # Define data paths
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    data_dir = os.path.join(project_root, 'data', 'knowledge_bases', 'waf')
    manifest_file = os.path.join(data_dir, 'manifest.json')
    index_dir = os.path.join(data_dir, 'index')
    
    # Check if manifest exists
    if not os.path.exists(manifest_file):
        print(f"❌ ERROR: {manifest_file} not found!")
        print("   Please run Phase 1 first: python scripts/ingest/waf_phase1.py")
        return
    
    # Load and check manifest
    import json
    with open(manifest_file, 'r') as f:
        manifest = json.load(f)
    
    approved_count = sum(1 for doc in manifest if doc['status'] == 'APPROVED')
    pending_count = sum(1 for doc in manifest if doc['status'] == 'PENDING_REVIEW')
    rejected_count = sum(1 for doc in manifest if doc['status'] == 'REJECTED')
    
    print(f"📊 Validation Status:")
    print(f"   ✅ APPROVED:       {approved_count}")
    print(f"   ⏳ PENDING_REVIEW: {pending_count}")
    print(f"   ❌ REJECTED:       {rejected_count}")
    print(f"   📄 TOTAL:          {len(manifest)}\n")
    
    if approved_count == 0:
        print("❌ ERROR: No APPROVED documents found!")
        print(f"   Please edit {manifest_file} and set status to 'APPROVED'")
        print("   for documents you want to include in the index.")
        return
    
    if pending_count > 0:
        print(f"⚠️  WARNING: {pending_count} documents still PENDING_REVIEW")
        response = input("   Continue with only APPROVED documents? (y/n): ")
        if response.lower() != 'y':
            print("\n❌ Aborted. Please complete validation first.")
            return
        print()
    
    # Build index
    print("Building vector index...")
    print("-" * 70 + "\n")
    
    builder = WAFIndexBuilder(
        chunk_size=800,
        chunk_overlap=120,
        storage_dir=index_dir
    )
    
    builder.build_index(manifest_file)
    
    print("\n" + "="*70)
    print("PHASE 2 COMPLETE - Index Ready for Queries!")
    print("="*70)
    print(f"\n📁 Index saved to: {index_dir}/")
    print(f"✅ Indexed {approved_count} approved documents")
    print(f"\n🚀 You can now query the WAF documentation!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()

