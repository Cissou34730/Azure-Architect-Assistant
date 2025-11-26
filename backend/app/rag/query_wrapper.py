"""
Query Wrapper for TypeScript Integration
Accepts JSON input from stdin and returns JSON output.
"""

import sys
import json
import os
import logging
from dotenv import load_dotenv
from query import WAFQueryService

# Load environment variables
load_dotenv()

# Configure logging to stderr so it doesn't interfere with JSON output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for query wrapper."""
    try:
        logger.info("[query_wrapper] Starting query processing")
        
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())
        
        question = input_data.get('question', '')
        top_k = input_data.get('top_k', 5)
        metadata_filters = input_data.get('metadata_filters')
        
        logger.info(f"[query_wrapper] Question: {question}, top_k: {top_k}")
        
        if not question:
            result = {
                'answer': 'No question provided',
                'sources': [],
                'scores': [],
                'has_results': False
            }
            print(json.dumps(result))
            return
        
        # Get storage directory from environment variable or use default
        storage_dir = os.getenv("WAF_STORAGE_DIR")
        logger.info(f"[query_wrapper] WAF_STORAGE_DIR from env: {storage_dir}")
        
        if storage_dir is None:
            # Fallback to calculated path
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
            storage_dir = os.path.join(project_root, "data", "knowledge_bases", "waf", "index")
            logger.info(f"[query_wrapper] Calculated storage_dir: {storage_dir}")
        
        logger.info(f"[query_wrapper] Final storage_dir: {storage_dir}")
        logger.info(f"[query_wrapper] Directory exists: {os.path.exists(storage_dir)}")
        
        if not os.path.exists(storage_dir):
            logger.error(f"[query_wrapper] Index directory not found at {storage_dir}")
            result = {
                'answer': 'WAF index not found. Please run the ingestion pipeline first.',
                'sources': [],
                'scores': [],
                'has_results': False,
                'error': 'INDEX_NOT_FOUND'
            }
            print(json.dumps(result))
            return
        
        # Initialize service and query
        logger.info("[query_wrapper] Initializing WAFQueryService")
        service = WAFQueryService(
            storage_dir=storage_dir,
            embedding_model="text-embedding-3-small",
            llm_model="gpt-4o-mini"
        )
        
        logger.info("[query_wrapper] Executing query")
        result = service.query_with_discussion(
            question=question,
            top_k=top_k,
            metadata_filters=metadata_filters
        )
        
        logger.info(f"[query_wrapper] Query completed. has_results: {result.get('has_results', False)}")
        
        # Output JSON result
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        logger.error(f"[query_wrapper] Error: {str(e)}", exc_info=True)
        error_result = {
            'answer': f'Error processing query: {str(e)}',
            'sources': [],
            'scores': [],
            'has_results': False,
            'error': str(e)
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == "__main__":
    main()
