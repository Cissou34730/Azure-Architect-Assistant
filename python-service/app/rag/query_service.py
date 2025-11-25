"""
Long-running Query Service
Keeps Python process alive and index loaded in memory for fast subsequent queries.
Accepts JSON queries on stdin, one per line, and returns JSON responses.
"""

import sys
import json
import os
import logging
from dotenv import load_dotenv
from .kb_query import WAFQueryService

# Load environment variables
load_dotenv()

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point - long-running service."""
    logger.info("[query_service] Starting long-running query service")
    
    # Get storage directory from environment
    storage_dir = os.getenv("WAF_STORAGE_DIR")
    logger.info(f"[query_service] WAF_STORAGE_DIR: {storage_dir}")
    
    if not storage_dir or not os.path.exists(storage_dir):
        logger.error(f"[query_service] Index not found at {storage_dir}")
        error_result = {
            'error': 'INDEX_NOT_FOUND',
            'message': 'WAF index not found'
        }
        print(json.dumps(error_result), flush=True)
        sys.exit(1)
    
    # Initialize service once (index will be cached)
    logger.info("[query_service] Initializing WAFQueryService (loading index...)")
    service = WAFQueryService(
        storage_dir=storage_dir,
        embedding_model="text-embedding-3-small",
        llm_model="gpt-4o-mini"
    )
    
    # Force index load on startup
    logger.info("[query_service] Pre-loading index into cache...")
    try:
        service._load_index()
        logger.info("[query_service] Index pre-loaded successfully. Service ready.")
        
        # Send ready signal
        ready_signal = {'status': 'ready'}
        print(json.dumps(ready_signal), flush=True)
    except Exception as e:
        logger.error(f"[query_service] Failed to load index: {str(e)}")
        error_result = {
            'error': 'LOAD_FAILED',
            'message': str(e)
        }
        print(json.dumps(error_result), flush=True)
        sys.exit(1)
    
    # Process queries from stdin
    logger.info("[query_service] Listening for queries on stdin...")
    for line in sys.stdin:
        try:
            line = line.strip()
            if not line:
                continue
            
            # Parse query
            query_data = json.loads(line)
            
            if query_data.get('command') == 'exit':
                logger.info("[query_service] Exit command received")
                break
            
            question = query_data.get('question', '')
            top_k = query_data.get('top_k', 3)
            metadata_filters = query_data.get('metadata_filters')
            
            if not question:
                result = {
                    'error': 'NO_QUESTION',
                    'message': 'No question provided'
                }
                print(json.dumps(result), flush=True)
                continue
            
            logger.info(f"[query_service] Processing: {question[:50]}...")
            
            # Execute query (fast because index is cached!)
            result = service.query_with_discussion(
                question=question,
                top_k=top_k,
                metadata_filters=metadata_filters
            )
            
            # Return result
            print(json.dumps(result, ensure_ascii=False), flush=True)
            
        except json.JSONDecodeError as e:
            logger.error(f"[query_service] Invalid JSON: {str(e)}")
            error_result = {
                'error': 'INVALID_JSON',
                'message': str(e)
            }
            print(json.dumps(error_result), flush=True)
        except Exception as e:
            logger.error(f"[query_service] Error: {str(e)}", exc_info=True)
            error_result = {
                'error': 'QUERY_FAILED',
                'message': str(e)
            }
            print(json.dumps(error_result), flush=True)
    
    logger.info("[query_service] Service shutting down")


if __name__ == "__main__":
    main()
