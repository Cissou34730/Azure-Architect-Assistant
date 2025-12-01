# Legacy POC Code - Archived

This directory contains legacy code from the initial POC phase that has been replaced by the modular architecture.

## Archived Components

### legacy_rag/
Original RAG implementation using stdin/stdout communication pattern:
- `query_service.py` - Long-running query service with stdin/stdout interface
- `query_wrapper.py` - JSON wrapper for TypeScript integration
- `query_stream_wrapper.py` - Streaming query wrapper
- `crawler.py` - Early WAF documentation crawler
- `cleaner.py` - Document cleaning pipeline
- `indexer.py` - Vector index builder
- `kb_query.py` - WAF query service
- `test_*.py` - Various test scripts

**Why archived:** Replaced by FastAPI REST endpoints with proper async/await patterns. The stdin/stdout pattern was fragile and difficult to debug.

### legacy_routers/
Old router implementations before modularization:
- `_kb_ingestion_old.py` - Original ingestion endpoints
- `_kb_old.py` - Original KB management
- `_projects_old.py` - Original project management
- `_query_old.py` - Original query endpoints
- `waf_ingestion_legacy.py` - WAF-specific ingestion

**Why archived:** Replaced by modular routers in `backend/app/routers/` with clear separation of routing layer, operations layer, and domain logic.

### migrations/
Database migration scripts:
- `migrate_data.py` - Data migration utilities
- `check_schema.py` - Schema validation
- `verify_migrated_data.py` - Migration verification

**Why archived:** One-time migration scripts no longer needed after successful migration to current schema.

## Current Architecture

The codebase now uses:
- **FastAPI REST endpoints** instead of stdin/stdout communication
- **Unified IngestionService** for job tracking (no duplicate JobManager)
- **Modular pipeline** with separate concerns for crawling, chunking, indexing
- **Non-blocking startup** with lazy index loading
- **Cooperative pause/resume/cancel** via async state flags

## Reference Date

Archived: November 30, 2025
Original implementation: Early 2024 - Mid 2025
