# WAF Checklist Normalization

Last updated: 2024-05-24

## Overview
This document describes the normalization of WAF (Well-Architected Framework) checklists from denormalized JSONB state in `ProjectState` to a structured, relational model.

## Rationale
- **Performance**: Querying specific checklist items or progress across many projects is slow with JSONB.
- **Data Integrity**: Enforce schema constraints on evaluations and statuses.
- **Reporting**: Easier to generate cross-project reports on common WAF gaps.
- **Concurrency**: Better handling of partial updates to checklists by different agents.

## Architecture
The system uses a Registry to load templates and an Engine to orchestrate the synchronization between the legacy JSON state and the normalized DB tables.

### Tables
- `checklists`: Project-specific checklist instances.
- `checklist_items`: Individual items within a checklist, linked to a template item.
- `checklist_item_evaluations`: History of evaluations (covered, partial, etc.) for an item.

## Operations
### Backfill
To migrate existing projects:
```bash
python scripts/backfill_waf.py --execute --verify
```

### Maintenance
To refresh templates or show stats:
```bash
python scripts/maintain_checklists.py stats
```

## API Reference
- `GET /api/projects/{id}/checklists`: List checklists for a project.
- `GET /api/projects/{id}/checklists/{checklist_id}`: Get checklist details.
- `GET /api/projects/{id}/checklists/progress`: Get completion percentage and breakdown.
- `POST /api/projects/{id}/checklists/items/{item_id}/evaluate`: Manual evaluation.
