"""
Query Wrapper for TypeScript Integration
Accepts JSON input from stdin and returns JSON output.
"""

import sys
import json
import os
from dotenv import load_dotenv
from query_service import WAFQueryService

# Load environment variables
load_dotenv()


def main():
    """Main entry point for query wrapper."""
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())
        
        question = input_data.get('question', '')
        top_k = input_data.get('top_k', 5)
        metadata_filters = input_data.get('metadata_filters')
        
        if not question:
            result = {
                'answer': 'No question provided',
                'sources': [],
                'scores': [],
                'has_results': False
            }
            print(json.dumps(result))
            return
        
        # Check if index exists
        storage_dir = os.path.join(os.path.dirname(__file__), 'waf_storage_clean')
        if not os.path.exists(storage_dir):
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
        service = WAFQueryService(
            storage_dir=storage_dir,
            embedding_model="text-embedding-3-small",
            llm_model="gpt-4-turbo-preview"
        )
        
        result = service.query_with_discussion(
            question=question,
            top_k=top_k,
            metadata_filters=metadata_filters
        )
        
        # Output JSON result
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
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
