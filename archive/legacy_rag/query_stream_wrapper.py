"""
Streaming Query Wrapper for TypeScript Integration
Accepts JSON input from stdin and streams JSON output line by line.
"""

import sys
import json
import os
import logging
from dotenv import load_dotenv
from query import WAFQueryService

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
    """Main entry point for streaming query wrapper."""
    try:
        logger.info("[query_stream_wrapper] Starting streaming query processing")
        
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())
        
        question = input_data.get('question', '')
        top_k = input_data.get('top_k', 3)
        metadata_filters = input_data.get('metadata_filters')
        
        logger.info(f"[query_stream_wrapper] Question: {question}, top_k: {top_k}")
        
        if not question:
            result = {
                'type': 'error',
                'content': 'No question provided',
                'done': True
            }
            print(json.dumps(result), flush=True)
            return
        
        # Get storage directory from environment variable
        storage_dir = os.getenv("WAF_STORAGE_DIR")
        logger.info(f"[query_stream_wrapper] WAF_STORAGE_DIR: {storage_dir}")
        
        if storage_dir and not os.path.exists(storage_dir):
            logger.error(f"[query_stream_wrapper] Index not found at {storage_dir}")
            result = {
                'type': 'error',
                'content': 'WAF index not found. Please run the ingestion pipeline first.',
                'done': True
            }
            print(json.dumps(result), flush=True)
            return
        
        # Initialize service
        logger.info("[query_stream_wrapper] Initializing WAFQueryService")
        service = WAFQueryService(
            storage_dir=storage_dir,
            embedding_model="text-embedding-3-small",
            llm_model="gpt-4o-mini"
        )
        
        logger.info("[query_stream_wrapper] Starting streaming query")
        
        # Stream response chunks
        for chunk in service.query_stream(
            question=question,
            top_k=top_k,
            metadata_filters=metadata_filters
        ):
            print(json.dumps(chunk, ensure_ascii=False), flush=True)
        
        logger.info("[query_stream_wrapper] Streaming complete")
        
    except Exception as e:
        logger.error(f"[query_stream_wrapper] Error: {str(e)}", exc_info=True)
        error_result = {
            'type': 'error',
            'content': f'Error processing query: {str(e)}',
            'done': True,
            'error': str(e)
        }
        print(json.dumps(error_result), flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
