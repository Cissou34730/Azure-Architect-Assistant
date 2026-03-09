# DATA_ROOT Storage Policy

All persisted backend runtime data must live under `DATA_ROOT`.

## Canonical Environment Variable

- `DATA_ROOT=/absolute/or/relative/path`

When relative, paths are resolved from repository root.

## Derived Runtime Paths

These paths are derived from `DATA_ROOT` unless explicitly overridden with env vars (and still must remain under `DATA_ROOT`):

- `PROJECTS_DATABASE` → `${DATA_ROOT}/projects.db`
- `INGESTION_DATABASE` → `${DATA_ROOT}/ingestion.db`
- `DIAGRAMS_DATABASE` → `${DATA_ROOT}/diagrams.db`
- `MODELS_CACHE_PATH` (`models_cache_path`) → `${DATA_ROOT}/openai_models_cache.json`
- `KNOWLEDGE_BASES_ROOT` → `${DATA_ROOT}/knowledge_bases`
- `PROJECT_DOCUMENTS_ROOT` (`project_documents_root`) → `${DATA_ROOT}/project_documents`
- `WAF_TEMPLATE_CACHE_DIR` (`waf_template_cache_dir`) → `${DATA_ROOT}/waf_template_cache`

## Enforcement

`AppSettings` validates at startup that all storage/database paths are inside `DATA_ROOT`.

During validation, `StorageSettingsMixin` also:

- normalizes relative storage paths against the backend root
- derives unset runtime paths from `DATA_ROOT`
- creates the parent directories needed for database/file paths and the directories needed for root paths

If any path is outside, startup fails with a clear validation error.

## Migration Notes

Legacy data previously written to workspace-local folders (`backend/data`, `backend/config/checklists`) must be moved under `DATA_ROOT`.

The current implementation already migrated:

- uploaded project documents
- OpenAI model list cache
- checklist template cache JSON files

## Operational Guidance

- Set `DATA_ROOT` explicitly in `.env` for every environment.
- Keep `DATA_ROOT` on durable storage in production.
- Do not point individual storage vars outside `DATA_ROOT`.
