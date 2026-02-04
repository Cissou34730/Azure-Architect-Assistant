Microsoft-only checklist sources

This folder contains authorized Microsoft Learn checklist templates used by the Azure Architect Assistant.

Policy:
- Only Microsoft Learn or Microsoft-owned guidance may be used as sources for templates in this folder.
- Each template JSON must include `source`, `source_url`, `source_version`, and `fetched_at` fields.
- Any remote fetch must be audited and approved before committing to the repository.

Current templates:
- microsoft_waf.json — canonical Azure WAF guidance (fetched from Microsoft Learn).

Importing new templates:
- Use `scripts/import_checklists_microsoft.py` (TBD) to fetch and normalize Microsoft Learn guidance via the MCP server or HTTP. The import script should validate licensing and add `source_license` metadata.
- Avoid manual edits to `original_content.fetched_text`; prefer to store canonical source and normalized `items` mapping.
