"""
WAF Ingestion - Phase 1: Document Cleaning & Export
Crawls WAF documentation and exports cleaned documents for manual validation.
"""

import sys
import os

# Add backend/src/python to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src', 'python'))

from crawler import WAFCrawler
from ingestion import WAFIngestionPipeline

def main():
    """Run Phase 1: Crawl and clean documents."""
    
    print("="*70)
    print("WAF INGESTION - PHASE 1")
    print("Crawl → Clean → Export for Validation")
    print("="*70 + "\n")
    
    # Step 1: Crawl
    print("STEP 1: Crawling WAF Documentation...")
    print("-" * 70)
    crawler = WAFCrawler(
        start_url="https://learn.microsoft.com/en-us/azure/well-architected/",
        max_pages=500,
        max_depth=3
    )
    urls = crawler.crawl()
    crawler.save_urls("waf_urls.txt")
    print(f"\nCrawled {len(urls)} URLs")
    print(f"Saved to: waf_urls.txt\n")
    
    # Step 2: Process and clean documents
    print("STEP 2: Processing and Cleaning Documents...")
    print("-" * 70)
    pipeline = WAFIngestionPipeline()
    documents = pipeline.process_urls_from_file("waf_urls.txt")
    print(f"\nProcessed {len(documents)} documents\n")
    
    # Step 3: Export for validation
    print("STEP 3: Exporting for Manual Validation...")
    print("-" * 70)
    pipeline.export_for_validation(
        documents,
        output_dir="cleaned_documents",
        manifest_file="validation_manifest.json"
    )
    
    print("\n" + "="*70)
    print("PHASE 1 COMPLETE")
    print("="*70)
    print(f"\nCleaned documents exported to: cleaned_documents/")
    print(f"Manifest created: validation_manifest.json")
    print(f"\n📋 NEXT STEPS:")
    print(f"   1. Review documents in cleaned_documents/")
    print(f"   2. Edit validation_manifest.json")
    print(f"   3. Set 'status' to 'APPROVED' or 'REJECTED' for each document")
    print(f"   4. Run Phase 2: python run_waf_phase2.py")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
