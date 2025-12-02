"""
Debug script to test crawler link extraction and URL validation.
Run this to diagnose why crawler stops early.
"""

import asyncio
import logging
from pathlib import Path
from backend.app.kb.ingestion.sources.website.crawler import WebsiteCrawler
from backend.app.models.ingestion import IngestionState

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_crawler():
    """Test crawler with verbose debugging"""
    
    # Test URL (CAF)
    start_url = "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/"
    url_prefix = "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/"
    
    # Create test state
    state = IngestionState(kb_id="test-caf", job_id=1)
    
    # Create crawler
    crawler = WebsiteCrawler(kb_id="test-caf", state=state)
    
    logger.info("="*70)
    logger.info("CRAWLER DEBUG TEST")
    logger.info("="*70)
    logger.info(f"Start URL: {start_url}")
    logger.info(f"URL Prefix: {url_prefix}")
    logger.info(f"Max Pages: 100 (reduced for testing)")
    logger.info("="*70)
    
    # Crawl with reduced max_pages for testing
    total_docs = 0
    total_batches = 0
    
    for batch in crawler.crawl(
        start_url=start_url,
        url_prefix=url_prefix,
        max_pages=100,  # Reduced for testing
        checkpoint_interval=10,
        batch_size=10
    ):
        total_batches += 1
        batch_size = len(batch)
        total_docs += batch_size
        
        logger.info(f"Batch {total_batches}: {batch_size} documents (total: {total_docs})")
        
        # Show first doc URL in each batch
        if batch:
            first_url = batch[0].metadata.get('url', 'unknown')
            logger.info(f"  First URL: {first_url}")
    
    logger.info("="*70)
    logger.info("CRAWLER TEST COMPLETE")
    logger.info("="*70)
    logger.info(f"Total batches: {total_batches}")
    logger.info(f"Total documents: {total_docs}")
    logger.info("="*70)
    
    # Check state file
    backend_root = Path(__file__).parent
    state_path = backend_root / "data" / "knowledge_bases" / "test-caf" / "state.json"
    
    if state_path.exists():
        import json
        with open(state_path, 'r') as f:
            state_data = json.load(f)
            crawl_state = state_data.get('crawl', {})
            
            logger.info("STATE FILE ANALYSIS:")
            logger.info(f"  Visited URLs: {len(crawl_state.get('visited_urls', []))}")
            logger.info(f"  Pending URLs: {len(crawl_state.get('pending_urls', []))}")
            logger.info(f"  Pages failed: {crawl_state.get('pages_failed', 0)}")
            
            # Show some visited URLs
            visited = crawl_state.get('visited_urls', [])
            if visited:
                logger.info(f"  Sample visited URLs (first 5):")
                for url in visited[:5]:
                    logger.info(f"    - {url}")
            
            # Show pending URLs if any
            pending = crawl_state.get('pending_urls', [])
            if pending:
                logger.info(f"  Pending URLs (first 10):")
                for url in pending[:10]:
                    logger.info(f"    - {url}")
            else:
                logger.info("  ⚠ NO PENDING URLs - crawler stopped because queue was empty!")

if __name__ == "__main__":
    asyncio.run(test_crawler())
