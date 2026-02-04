# Production Backfill Log - WAF Normalization

## Metadata
- **Date**: February 4, 2026
- **Operator**: Copilot
- **Environment**: Production (Local DB: `backend/data/projects.db`)
- **Backfill Script**: `backend/scripts/backfill_waf.py`
- **Total Records in DB**: 15 (14 original + 1 test record)

## Dry-run Execution
- **Command**: `python backend/scripts/backfill_waf.py --dry-run`
- **Results**:
  - Found 1 project with WAF findings.
  - Successfully mapped 1 project to `azure-waf-v1` template.
  - 0 errors reported.
- **Log Snippet**:
  ```
  INFO:app.services.backfill_service:Starting backfill: total=1, dry_run=True
  INFO:app.services.backfill_service:Backfill progress: processed=1, total=1
  ```

## Actual Execution
- **Command**: `python backend/scripts/backfill_waf.py --verify`
- **Results**:
  - Processed 1 project.
  - 0 errors reported.
  - Verification: 1 checklist, 2 items, 2 evaluations created.
- **Verification Query**:
  ```sql
  SELECT count(*) FROM checklists; -- Result: 1
  SELECT count(*) FROM checklist_items; -- Result: 2
  SELECT count(*) FROM checklist_item_evaluations; -- Result: 2
  ```

## Post-Backfill Integrity Check
- [x] Deterministic IDs verified (rerun script results in 0 new records)
- [x] Column parity: `checklist_items` has `template_item_id` and `pillar`
- [x] Evaluation parity: `checklist_item_evaluations` has `comment`

## Issues Encountered
1. **Migration Column Mismatch**: Initial migration was missing `template_slug`, `version` in `checklists` and `comment` in `checklist_item_evaluations`. Fixed and reran.
2. **SQLite Pattern Matching**: Query for WAF Findings in JSON needed `.like('%"wafChecklist"%')` instead of JSON extract for simplicity/reliability.
3. **Logging Incompatibility**: Removed `structlog` style logs from backfill script to match standard logging.

## Status: COMPLETE
