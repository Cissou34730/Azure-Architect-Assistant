# Prompt System Refactoring

**Date:** 2025-12-11  
**Status:** ✅ Complete

## Problem

System prompts were hardcoded in Python module (`react_prompts.py`):
- Required code restart for any prompt changes
- Hard for non-developers to edit
- Difficult to A/B test different prompts
- No clear version control for prompt evolution

## Solution

Moved prompts to external YAML configuration:
- **Location:** `backend/config/prompts/agent_prompts.yaml`
- **Loader:** `PromptLoader` class in `prompt_loader.py`
- **Backward compatible:** Existing code still imports from `react_prompts.py`

## Benefits

### 1. Dynamic Updates
```yaml
# Edit prompts directly in YAML
system_prompt: |
  You are an Azure Architecture Assistant...
```
Changes take effect on next agent initialization (no code deployment).

### 2. Easy Editing
- Plain text YAML format
- Human-readable diffs in git
- Non-developers can edit prompts
- Clear structure and organization

### 3. Version Control
- Track prompt evolution over time
- See exactly what changed
- Easy rollback to previous versions
- Document why changes were made

### 4. A/B Testing
- Maintain multiple prompt files
- Switch by environment variable
- Compare effectiveness
- Iterate quickly

## Architecture

```
backend/
├── config/
│   └── prompts/
│       ├── agent_prompts.yaml      # Main prompts file
│       └── README.md                # Documentation
│
└── app/
    └── agents_system/
        └── config/
            ├── prompt_loader.py     # YAML loader with caching
            └── react_prompts.py     # Thin wrapper (backward compat)
```

### How It Works

1. **PromptLoader** reads YAML on first access
2. Results are **cached** for performance
3. **react_prompts.py** provides constants for backward compatibility
4. Existing code works without changes

```python
# Old code (still works)
from app.agents_system.config.react_prompts import SYSTEM_PROMPT

# New capability
from app.agents_system.config.react_prompts import reload_prompts
reload_prompts()  # Hot-reload from file
```

## YAML Structure

```yaml
version: "1.0"
last_updated: "2025-12-11"

system_prompt: |
  # Main system instructions
  
react_template: |
  # ReAct reasoning format
  
clarification_prompt: |
  # Clarification question template
  
conflict_resolution_prompt: |
  # Option presentation template
  
few_shot_examples:
  - name: "Example 1"
    question: "..."
    reasoning: |
      Thought: ...
      Action: ...
```

## Usage

### Edit Prompts
1. Open `backend/config/prompts/agent_prompts.yaml`
2. Edit the desired prompt
3. Save file
4. Restart backend (or call reload API when implemented)

### Test Changes
```bash
# Load and verify
cd backend
python -c "from app.agents_system.config import react_prompts; \
  print('Loaded:', len(react_prompts.SYSTEM_PROMPT), 'chars')"
```

### Hot Reload (Future)
```python
# Add to lifecycle.py
from watchfiles import awatch

async def watch_prompts():
    async for changes in awatch('backend/config/prompts'):
        reload_prompts()
```

## Migration

- ✅ All prompts moved to YAML
- ✅ PromptLoader implemented with caching
- ✅ Backward compatibility maintained
- ✅ Documentation added
- ✅ Tested and working
- ⏳ Hot reload API endpoint (future)
- ⏳ File watcher for auto-reload (future)

## Files Changed

| File | Change |
|------|--------|
| `config/prompts/agent_prompts.yaml` | NEW - All prompts in YAML |
| `config/prompts/README.md` | NEW - Documentation |
| `app/agents_system/config/prompt_loader.py` | NEW - YAML loader |
| `app/agents_system/config/react_prompts.py` | REFACTORED - Now loads from YAML |

## Next Steps

1. **Test prompt iterations** - Make small changes, measure impact
2. **Add hot reload API** - Reload without restart
3. **Implement file watcher** - Auto-reload on file change
4. **Create prompt variants** - A/B test different approaches
5. **Track metrics** - Success rate, parsing errors, user feedback

## Example: Making a Change

```yaml
# Before
system_prompt: |
  You are an Azure Architecture Assistant...

# After (edit YAML)
system_prompt: |
  You are an expert Azure Architecture Assistant...
  
# Restart backend
npm run backend

# Change is live!
```

## Notes

- PyYAML already in requirements (6.0.3)
- Path resolves correctly from any import location
- Errors are logged with helpful messages
- Empty cache on reload for fresh reads
