Microsoft-only checklist sources

This folder contains authorized Microsoft Learn checklist templates used by the Azure Architect Assistant.

Policy:
- Only Microsoft Learn or Microsoft-owned guidance may be used as sources for templates in this folder.
- Each template JSON must include `source`, `source_url`, `source_version`, and `fetched_at` fields.
- Any remote fetch must be audited and approved before committing to the repository.

Current templates:
- azure-waf-reliability-v1.json
- azure-waf-security-v1.json
- azure-waf-cost-optimization-v1.json
- azure-waf-operational-excellence-v1.json
- azure-waf-performance-efficiency-v1.json

Importing new templates:
- Use `backend/scripts/import_waf_templates_from_mcp.py` to fetch and normalize Microsoft Learn guidance via the MCP server. The import script writes the five pillar templates and stamps `source_license` + `fetched_at` metadata.
- Avoid manual edits to `original_content.fetched_text`; prefer to store canonical source and normalized `items` mapping.
