# ProjectState Inventory

Generated on 2026-04-01 from the local projects database with:

`uv run python scripts/audit_project_state_blob.py --emit-markdown --markdown-output docs/architecture/PROJECTSTATE_DECOMPOSITION_INVENTORY.md`

## Immediate findings

- The blob is still a live store for much more than architecture inputs.
- No malformed or empty rows were found in the current sample.
- Both camelCase and snake_case variants are present for several artifact families, which increases migration complexity.
- Candidate architectures, ADRs, findings, diagrams, WAF data, IaC artifacts, cost estimates, traceability data, and reference documents all appear in the blob today.

That means Phase 4 cannot assume only `context`, `nfrs`, `applicationStructure`, `dataCompliance`, `technicalConstraints`, and `openQuestions` remain in `ProjectState.state`.

## Raw audit output

## Summary

- Rows scanned: 30
- JSON object rows: 30
- Empty rows: 0
- Malformed rows: 0
- Non-object rows: 0

## Top-level keys

| Key | Count |
| --- | ---: |
| adrs | 28 |
| analysisSummary | 3 |
| applicationStructure | 25 |
| assumptions | 28 |
| candidateArchitectures | 20 |
| candidate_architectures | 8 |
| clarificationQuestions | 21 |
| clarification_questions | 8 |
| context | 25 |
| costEstimates | 20 |
| cost_estimates | 8 |
| dataCompliance | 25 |
| decisions | 1 |
| diagrams | 28 |
| findings | 28 |
| iacArtifacts | 20 |
| iac_artifacts | 8 |
| ingestionStats | 18 |
| ingestion_stats | 8 |
| iterationEvents | 20 |
| iteration_events | 8 |
| mcpQueries | 20 |
| mcp_queries | 8 |
| mindMap | 20 |
| mindMapCoverage | 20 |
| mind_map | 8 |
| mind_map_coverage | 8 |
| nfrs | 25 |
| openQuestions | 25 |
| projectDocumentStats | 7 |
| referenceDocuments | 20 |
| reference_documents | 8 |
| requirements | 29 |
| technicalConstraints | 25 |
| traceabilityIssues | 20 |
| traceabilityLinks | 20 |
| traceability_issues | 8 |
| traceability_links | 8 |
| wafChecklist | 18 |
| waf_checklist | 8 |

## Empty rows

- None

## Malformed rows

- None

## Non-object rows

- None
