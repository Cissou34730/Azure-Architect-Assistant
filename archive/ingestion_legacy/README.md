# Legacy Ingestion Code Archive

This directory contains the old ingestion implementation before the refactoring to layered architecture.

**Archived on**: December 2, 2025  
**Reason**: Debugging and reference for comparison with new implementation

## Contents

### `service_components/`
Original tightly-coupled implementation before layered architecture refactoring.

**Files:**
- `manager.py` - Old IngestionService (monolithic)
- `repository.py` - Direct database functions (no interface)
- `storage.py` - Direct file persistence (no interface)
- `producer.py` - Producer worker (old version)
- `consumer.py` - Consumer worker (old version)
- `runtime.py` - JobRuntime model
- `state.py` - IngestionState model
- `__init__.py` - Package exports

### `data_old/`
Old data directory from `backend/app/ingestion/data/` before consolidation.

**Contains:**
- `knowledge_bases/caf/` - Old CAF state.json and temp files
- Legacy data from before migration to `backend/data/knowledge_bases/`

**Note:** The active data directory is now `backend/data/knowledge_bases/`, which contains all current KB data (CAF, WAF, NIST-SP).

## Why Archived

The original `service_components` implementation had several limitations:
- **Tight coupling**: Direct dependencies on concrete implementations
- **No dependency injection**: Hard to test and mock
- **Mixed concerns**: Business logic mixed with infrastructure
- **Hard-coded configuration**: No centralized settings
- **Limited extensibility**: Difficult to add custom backends

## New Implementation

The refactored code (in `backend/app/ingestion/`) addresses these issues:

```
backend/app/ingestion/
├── domain/              # Business logic and interfaces
├── infrastructure/      # Concrete implementations
├── application/         # Service orchestration
├── workers/             # Producer/consumer
├── config/              # Typed configuration
└── observability/       # Logging and metrics
```

## Using This Archive

### For Debugging
If you encounter issues with the new implementation, compare with the old code:

```bash
# Old implementation
archive/ingestion_legacy/service_components/manager.py

# New implementation  
backend/app/ingestion/application/ingestion_service.py
```

### For Reference
Key differences to understand:

1. **State Management**
   - Old: `service_components/state.py`
   - New: `domain/models/state.py` with pydantic schemas

2. **Repository**
   - Old: `service_components/repository.py` (direct functions)
   - New: `infrastructure/repository.py` (protocol-based)

3. **Persistence**
   - Old: `service_components/storage.py` (direct file ops)
   - New: `infrastructure/persistence.py` (interface-based)

4. **Configuration**
   - Old: Hard-coded values scattered throughout
   - New: `config/settings.py` with JSON configuration

## Restoration (if needed)

If you need to temporarily restore the old implementation:

```bash
cd backend/app/ingestion
cp -r ../../../archive/ingestion_legacy/service_components ./
```

**Note**: This is NOT recommended. The new implementation is more robust and maintainable.

## Related Documentation

- [Migration Applied](../docs/ingestion/MIGRATION_APPLIED.md)
- [Refactoring Complete](../docs/ingestion/REFACTORING_COMPLETE.md)
- [Architecture Guide](../docs/ingestion/ARCHITECTURE.md)

## Status

✅ New implementation is production-ready  
✅ All routers updated to use new code  
✅ Tests passing  
✅ Documentation complete  

This archive is for reference only.
