# KB Module (Management)

Purpose: Manage configuration and lifecycle of knowledge bases.

- Contains `KBManager` and `KBConfig` (in `models.py`).
- Manages config.json, storage paths, and KB metadata.
- Does not perform query execution or index building.

Usage:

```python
from app.kb import KBManager
manager = KBManager()
active = manager.get_active_kbs()
```
