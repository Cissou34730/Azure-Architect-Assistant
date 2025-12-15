# KB Services (Query)

Purpose: Execute queries against KB indices, and orchestrate multi-KB queries.

- `KBQueryService`: per-KB query using vector index and LLM.
- `MultiKBQueryService`: aggregates results across KBs and merges sources.
- `QueryProfile`: selects chat vs proposal behavior.

Usage:

```python
from app.services.kb import MultiKBQueryService, QueryProfile
from app.kb import KBManager

svc = MultiKBQueryService(KBManager())
result = svc.query_profile("What is WAF?", QueryProfile.CHAT)
```