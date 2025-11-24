# Knowledge Base Ingestion Scripts

This directory contains scripts for ingesting documentation into the RAG system.

## Current Knowledge Bases

### WAF (Azure Well-Architected Framework)

**Phase 1: Crawl & Clean**
```bash
python scripts/ingest/waf_phase1.py
```
- Crawls WAF documentation from Microsoft Learn
- Cleans and normalizes HTML content
- Exports markdown files to `data/knowledge_bases/waf/documents/`
- Creates validation manifest at `data/knowledge_bases/waf/manifest.json`

**Review Documents**
- Manually review exported documents in `data/knowledge_bases/waf/documents/`
- Edit `data/knowledge_bases/waf/manifest.json` to approve/reject documents
- Or auto-approve all: `python scripts/utils/approve_documents.py`

**Phase 2: Build Index**
```bash
python scripts/ingest/waf_phase2.py
```
- Processes approved documents
- Chunks text (800 tokens, 120 overlap)
- Generates embeddings via OpenAI
- Builds vector index at `data/knowledge_bases/waf/index/`

## Adding New Knowledge Bases

1. Create new directory: `data/knowledge_bases/<kb_id>/`
2. Create ingestion script: `scripts/ingest/<kb_id>_phase1.py`
3. Update `data/knowledge_bases/config.json`
4. Follow the same two-phase pattern

## Configuration

- Chunk size: 800 tokens
- Chunk overlap: 120 tokens
- Embedding model: text-embedding-3-small
- Generation model: gpt-4o-mini

See `data/knowledge_bases/config.json` for all KB configurations.
