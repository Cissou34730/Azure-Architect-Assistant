# Deprecation Plan - Legacy WAF JSON Storage

## Overview
Currently, WAF findings are stored as a blobs in the `project_states` table. The goal is to move entirely to the normalized `checklists` tables and eventually remove the `wafChecklist` field from the project state JSON.

## Phase 1: Dual-Write (Current)
- **Status**: ACTIVE
- **Behavior**: System writes to both legacy JSON and normalized tables.
- **Verification**: `normalize_helpers.validate_normalized_consistency` runs on every write.
- **Duration**: 2-4 weeks.

## Phase 2: Read-From-New
- **Status**: PLANNED
- **Behavior**: App logic reads WAF data primarily from normalized tables. Legacy JSON is kept as backup and for fallback.
- **Verification**: Periodic audit scripts to compare JSON vs DB.
- **Duration**: 2 weeks.

## Phase 3: Stop Legacy Writes
- **Status**: PLANNED
- **Behavior**: App stops writing to the `wafChecklist` field in JSON.
- **Verification**: Monitor consistency metrics (they should drop to zero as JSON becomes stale).

## Phase 4: Final Cleanup
- **Status**: PLANNED
- **Behavior**: 
  - Run one final backfill to ensure all projects are migrated.
  - Drop the fallback reading logic.
  - Update `AAAProjectState` model to remove legacy WAF fields.
  - Optional: Cleanup script to strip WAF data from legacy JSON blobs in DB to save space.

## Timeline
- **Feb 4**: Dual-write enabled.
- **Feb 18**: Start reading from new tables in staging.
- **Mar 1**: Stop legacy writes in production.
- **Mar 15**: Full cleanup.

## Stakeholders
- Backend Engineering
- Frontend (for component data structure changes)
- Data Platform team
