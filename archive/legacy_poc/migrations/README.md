# Migration Archive

This folder contains scripts used for the v3.0 → v4.0 migration from TypeScript backend to unified Python backend.

## Files

- **migrate_data.py** - Migrates data from old TypeScript SQLite schema to new Python SQLAlchemy schema
- **check_schema.py** - Verifies schema compatibility before migration
- **verify_migrated_data.py** - Validates data integrity after migration

## Usage (Historical Reference Only)

These scripts were used during the migration process and are kept for reference. The migration has been completed.

```python
# Check schema compatibility
python check_schema.py

# Perform data migration
python migrate_data.py

# Verify migrated data
python verify_migrated_data.py
```

## Migration Summary

- **Date**: November 2025
- **From**: TypeScript backend (Express + TypeORM) on port 3000
- **To**: Python backend (FastAPI + SQLAlchemy) on port 8000
- **Data Migrated**: 1 project, 8 messages, 1 project state
- **Status**: ✅ Complete and verified
