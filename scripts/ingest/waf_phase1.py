"""
WAF Ingestion - Phase 1: Document Cleaning & Export
Crawls WAF documentation and exports cleaned documents for manual validation.
"""

import sys
import os

# Add backend/src/rag to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(project_root, 'backend', 'src', 'rag'))

from crawler import WAFCrawler
from cleaner import WAFIngestionPipeline

def main():
    """Run Phase 1: Crawl and clean documents."""
    
    print("="*70)
    print("WAF INGESTION - PHASE 1")
    print("Crawl -> Clean -> Export for Validation")
    print("="*70 + "\n")
    
    # Define data paths
    data_dir = os.path.join(project_root, 'data', 'knowledge_bases', 'waf')
    urls_file = os.path.join(data_dir, 'urls.txt')
    docs_dir = os.path.join(data_dir, 'documents')
    manifest_file = os.path.join(data_dir, 'manifest.json')
    
    # Step 1: Crawl
    print("STEP 1: Crawling WAF Documentation...")
    print("-" * 70)
    crawler = WAFCrawler(
        start_url="https://learn.microsoft.com/en-us/azure/well-architected/",
        max_pages=500,
        max_depth=3
    )
    urls = crawler.crawl()
    crawler.save_urls(urls_file)
    print(f"\nCrawled {len(urls)} URLs")
    print(f"Saved to: {urls_file}\n")
    
    # Step 2: Process and clean documents
    print("STEP 2: Processing and Cleaning Documents...")
    print("-" * 70)
    pipeline = WAFIngestionPipeline()
    documents = pipeline.process_urls_from_file(urls_file)
    print(f"\nProcessed {len(documents)} documents\n")
    
    # Step 3: Export for validation
    print("STEP 3: Exporting for Manual Validation...")
    print("-" * 70)
    pipeline.export_for_validation(
        documents,
        output_dir=docs_dir,
        manifest_file=manifest_file
    )
    
    print("\n" + "="*70)
    print("PHASE 1 COMPLETE")
    print("="*70)
    print(f"\nCleaned documents exported to: {docs_dir}/")
    print(f"Manifest created: {manifest_file}")
    print(f"\n📋 NEXT STEPS:")
    print(f"   1. Review documents in {docs_dir}/")
    print(f"   2. Edit {manifest_file}")
    print(f"   3. Set 'status' to 'APPROVED' or 'REJECTED' for each document")
    print(f"   4. Run Phase 2: python scripts/ingest/waf_phase2.py")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()

