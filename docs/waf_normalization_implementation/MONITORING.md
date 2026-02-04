# Monitoring and Alerts - WAF Normalization

## Overview
This document describes the monitoring strategy for the normalized WAF checklist system. As the system moves from legacy JSON storage to normalized SQL tables, we must ensure data consistency and performance.

## Key Metrics

### 1. Data Consistency (Dual-Write Period)
- **Metric**: `waf_normalization_consistency_mismatch_count`
- **Description**: Number of times a read from legacy state does not match the results denormalized from the new tables.
- **Criticality**: HIGH
- **Alert**: Trigger if > 0 in any 1-hour window.

### 2. Backfill Progress
- **Metric**: `waf_backfill_processed_total`
- **Description**: Total number of projects successfully backfilled.
- **Metric**: `waf_backfill_errors_total`
- **Alert**: Trigger if error rate > 5% during execution.

### 3. API Performance
- **Metric**: `waf_api_latency_seconds` (Histogram)
- **Description**: Latency of `GET /projects/{id}/checklists` and `POST` updates.
- **Target**: p95 < 200ms.

### 4. Search Performance
- **Metric**: `waf_search_duration_seconds`
- **Description**: Time taken for cross-project WAF item queries.

## Log Analysis
Dashboard filters should be set up for:
- `logger="app.agents_system.checklists.engine"`
- `level="ERROR"`
- Key identifiers: `project_id`, `template_slug`.

## Alerts Configuration

| Alert Name | Condition | Severity | Action |
|------------|-----------|----------|--------|
| WAFConsistencyCritical | Mismatch count > 0 | P1 | Investigate `sync_project_state_to_db` logic. |
| WAFBackfillFailed | Errors > 10 in 5min | P2 | Pause backfill script and check logs. |
| WAFDatabaseLatency | p95 > 500ms | P3 | Check table indexes and query plan. |

## Dashboards
- [Internal Grafana Link] (Placeholder)
- [Prometheus Targets] (Placeholder)
