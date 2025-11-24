# Environment Configuration - Shared vs Separate

## Decision: Use Single Shared .env File ✅

### Structure
```
project/
├── .env              # ⭐ Single config (shared)
├── backend/          # Reads from ../.env
├── python-service/   # Reads from ../../.env
└── frontend/
```

### Why Single .env?

✅ **No duplication** - OPENAI_API_KEY in one place  
✅ **Always in sync** - Can't get out of sync  
✅ **Simpler setup** - One file to configure  
✅ **Better for POC** - Less overhead  

### Configuration in .env
```env
# OpenAI (used by both services)
OPENAI_API_KEY=sk-...

# Ports
EXPRESS_PORT=3000
PYTHON_SERVICE_PORT=8000

# Service URLs  
PYTHON_SERVICE_URL=http://localhost:8000

# Storage
WAF_STORAGE_DIR=./data/knowledge_bases/waf/index
```

### How Services Load It

**Express Backend** (`backend/`):
```typescript
// Loads from ../.env automatically (dotenv)
import 'dotenv/config';
```

**Python Service** (`python-service/`):
```python
# Explicitly loads from ../../.env
from pathlib import Path
from dotenv import load_dotenv

root_dir = Path(__file__).parent.parent.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)
```

## Alternative: Separate .env Files

For **production with separate deployments**, you might want:

```
backend/.env              # Express-specific config
python-service/.env       # Python-specific config
```

**When to use separate files:**
- Services deployed to different environments
- Different API keys per service
- Different security/compliance requirements
- Services managed by different teams

**For this POC:** Single shared `.env` is cleaner and simpler.

---

**Current Setup**: ✅ Single shared `.env` at project root
