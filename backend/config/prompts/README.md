# Agent Prompts Configuration

This directory contains agent prompts in YAML format for easy editing without code changes.

## Quick Start

**Edit prompts:** Modify `agent_prompts.yaml`  
**Apply changes:** Restart the backend or call the reload API endpoint

## Files

- **agent_prompts.yaml** - Main prompts configuration file

## Structure

```yaml
version: "1.0"
system_prompt: |
  # Main system instructions for the agent
  
react_template: |
  # ReAct reasoning template with format rules
  
clarification_prompt: |
  # Template for asking clarification questions
  
conflict_resolution_prompt: |
  # Template for presenting options when confidence is low
  
few_shot_examples:
  - name: "Example Name"
    question: "User question"
    reasoning: |
      # Complete ReAct trace showing expected behavior
```

## Benefits

### 1. Dynamic Updates
- Edit prompts without modifying code
- Changes take effect on next agent initialization
- No deployment required for prompt iterations

### 2. Version Control
- YAML diffs are human-readable
- Track prompt evolution over time
- Easy rollback to previous versions

### 3. A/B Testing
- Maintain multiple prompt files
- Switch between variants by environment
- Compare effectiveness easily

### 4. Collaboration
- Non-developers can edit prompts
- Clear separation of concerns
- Easier to review prompt changes

## Usage

### Python Code

```python
from app.agents_system.config import react_prompts

# Access prompts (loaded from YAML)
system_prompt = react_prompts.SYSTEM_PROMPT
react_template = react_prompts.REACT_TEMPLATE

# Force reload prompts (for hot-reload)
react_prompts.reload_prompts()

# Get loader for advanced usage
loader = react_prompts.get_prompt_loader()
loader.reload()
```

### API Endpoint (TODO)

```bash
# Reload prompts without restarting
POST /api/agents/reload-prompts
```

## Editing Guidelines

### System Prompt

The system prompt defines:
- Agent role and scope
- Core methodology (WAF, C4, workload classification)
- Behavior rules (clarification, confidence-based recommendations)
- Tool usage guidelines
- Output structure requirements
- Guardrails

**When editing:**
- Keep methodology sections clear and structured
- Use bold headings for scanability
- Be explicit about mandatory vs optional behaviors
- Include specific examples where helpful

### ReAct Template

The ReAct template defines the reasoning format.

**Critical elements:**
- Format rules MUST be at the top (LLM sees them first)
- Use imperative language ("MUST", "Never")
- Show exact format structure
- Include placeholder explanations

**Testing:**
- After changes, verify agent follows format correctly
- Check that parsing errors don't occur
- Ensure tools are called appropriately

### Few-Shot Examples

Examples demonstrate expected behavior.

**Requirements:**
- Show complete ReAct traces (Thought → Action → Observation → Final Answer)
- Cover different scenarios (high confidence, moderate confidence, clarification needed)
- Include proper tool usage
- Reference WAF pillars and C4 appropriately
- Cite sources in Final Answer

## Hot Reload (Future)

To enable hot reload without restart:

1. Add file watcher in lifecycle.py
2. Create reload endpoint in router
3. Call `reload_prompts()` when file changes

```python
# In lifecycle.py
from watchfiles import awatch

async def watch_prompts():
    async for changes in awatch('backend/config/prompts'):
        logger.info("Prompts changed, reloading...")
        reload_prompts()
```

## Best Practices

1. **Test Before Committing**
   - Restart backend
   - Run sample queries
   - Verify agent behavior

2. **Document Changes**
   - Update version in YAML
   - Note changes in commit message
   - Track prompt evolution in docs

3. **Keep Backups**
   - Git tracks all versions
   - Tag stable prompts
   - Document why changes were made

4. **Measure Impact**
   - Track agent success rate
   - Monitor parsing errors
   - Collect user feedback

## Troubleshooting

### FileNotFoundError
- Check that `agent_prompts.yaml` exists
- Verify path in `prompt_loader.py`
- Ensure working directory is correct

### YAMLError
- Validate YAML syntax (use online validator)
- Check indentation (use spaces, not tabs)
- Escape special characters in strings

### Agent Behavior Issues
- Review system prompt clarity
- Check ReAct format rules
- Verify examples are correct
- Test with verbose logging

### Prompts Not Updating
- Restart backend (hot reload not yet implemented)
- Clear Python cache: `find . -type d -name __pycache__ -exec rm -rf {} +`
- Check logs for load errors
