#!/usr/bin/env python3
"""
Master orchestration script for WAF ingestion pipeline.
Runs all steps sequentially with progress tracking.
"""

import sys
import os
from pathlib import Path

# Add the python directory to the path
script_dir = Path(__file__).parent
python_dir = script_dir / 'backend' / 'src' / 'python'
sys.path.insert(0, str(python_dir))

os.chdir(python_dir)

def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80 + "\n")

def main():
    """Run the complete ingestion pipeline."""
    try:
        print_header("WAF INGESTION PIPELINE")
        print("This script will crawl, process, and index Azure WAF documentation.")
        print("Estimated time: 15-30 minutes")
        print("Ensure OPENAI_API_KEY is set in your .env file\n")
        
        input("Press Enter to continue or Ctrl+C to cancel...")
        
        # Step 1: Crawl
        print_header("STEP 1/4: Crawling WAF Documentation")
        from crawler import WAFCrawler
        
        crawler = WAFCrawler(
            start_url="https://learn.microsoft.com/azure/well-architected/",
            max_depth=3,
            max_pages=500,
            delay=0.5
        )
        urls = crawler.crawl()
        crawler.save_urls("waf_urls.txt")
        print(f"✓ Discovered {len(urls)} URLs")
        
        # Step 2: Ingest
        print_header("STEP 2/4: Processing Documents")
        from ingestion import WAFIngestionPipeline
        
        pipeline = WAFIngestionPipeline()
        documents = pipeline.process_urls_from_file("waf_urls.txt")
        pipeline.save_documents(documents, "waf_documents.jsonl")
        print(f"✓ Processed {len(documents)} documents")
        
        # Step 3: Chunk
        print_header("STEP 3/4: Chunking Documents")
        from chunker import ChunkValidator
        
        validator = ChunkValidator(chunk_size=800, chunk_overlap=120)
        docs = validator.load_documents("waf_documents.jsonl")
        chunks = validator.chunk_all_documents(docs)
        
        # Auto-validate all chunks for POC
        chunks = validator.auto_validate_all(chunks)
        validator.export_for_validation(chunks)
        print(f"✓ Created {len(chunks)} chunks (auto-validated)")
        
        # Step 4: Index
        print_header("STEP 4/4: Building Vector Index")
        print("This step will generate embeddings (may take 10-20 minutes)...")
        from indexer import WAFIndexer
        
        indexer = WAFIndexer(
            storage_dir="waf_storage_clean",
            embedding_model="text-embedding-3-small",
            llm_model="gpt-4-turbo-preview"
        )
        indexer.build_and_persist("chunks_review.jsonl")
        print("✓ Vector index built and persisted")
        
        print_header("INGESTION COMPLETE")
        print("The WAF query system is now ready to use!")
        print("\nYou can now:")
        print("  1. Use the web interface to query WAF documentation")
        print("  2. Run: python query_service.py 'your question here'")
        print("  3. Test the REST API at /api/waf/query")
        
    except KeyboardInterrupt:
        print("\n\nIngestion cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
