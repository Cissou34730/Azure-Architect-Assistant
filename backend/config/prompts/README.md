# Agent Prompts Configuration

This directory contains agent prompts in YAML format for easy editing without code changes.

## Quick Start

**Edit prompts:** Modify the relevant modular YAML file (see Prompt Stack Layers below)  
**Apply changes:** Restart the backend or call the reload API endpoint

## Prompt Stack Layers (P13)

The prompt stack has a clear layered architecture. Each layer has a single responsibility:

| Layer | File | Purpose |
|---|---|---|
| 1 — Global quality | `constitution.yaml` | Overrides all; thoroughness, completeness, persist-before-responding |
| 2 — Role / Persona | `base_persona.yaml` | AAA identity, core methodology, delivery stance |
| 3 — Output contract | `architect_briefing.yaml` | Stage-aware Architect Briefing structure (NEW — P1) |
| 4 — Tool contract | `tool_strategy.yaml` | When and how to use KB/AAA/MCP tools |
| 5 — Quality rubric | `guardrails.yaml` | Anti-hallucination, reviewability, no raw artifact dumps |
| 6 — Stage routing | `orchestrator_routing.yaml` | Orchestrator delegation logic |
| 6 — Agent-specific | `<agent>_prompt.yaml` | Per-agent specialization |
| Fallback | `agent_prompts.yaml` | Legacy monolithic fallback; kept for compatibility |

## Files

- **agent_prompts.yaml** - Legacy monolithic prompt configuration and compatibility fallback (see P13 header comment inside)
- **constitution.yaml** - Global quality directives that override all other layers
- **base_persona.yaml** - Shared AAA persona and methodology
- **architect_briefing.yaml** - Stage-aware output contract: required Architect Briefing structure (P1)
- **orchestrator_routing.yaml** - Orchestrator-specific stage routing instructions
- **tool_strategy.yaml** - Shared tool selection rules
- **guardrails.yaml** - Shared hallucination/reviewability guardrails
- **clarification_planner.yaml** - Clarification-stage instructions
- **architecture_planner_prompt.yaml** - Architecture proposal prompt with C4/NFR guidance
- **adr_writer.yaml** - ADR-stage instructions
- **waf_validator.yaml** - Validation-stage instructions
- **requirements_extraction.yaml** - Source-grounded requirements extraction instructions

## Modular composition

`PromptLoader.compose_prompt(agent_type, stage, context_budget)` assembles a system prompt in this order:

1. `constitution.yaml` (always first — global quality overrides)
2. agent-specific prompt (for example `orchestrator_routing.yaml`)
3. stage-specific prompt (for example `clarification_planner.yaml`)
4. `base_persona.yaml`
5. `architect_briefing.yaml` ← **NEW (P1)** — stage-aware output contract
6. `tool_strategy.yaml`
7. `guardrails.yaml`

Each module can interpolate `${agent_type}`, `${stage}`, and `${context_budget}`.

If none of the modular files are present, the loader falls back to `agent_prompts.yaml`.

## Architect Briefing Contract (P1)

`architect_briefing.yaml` defines what every chat response MUST contain after persisting artifacts.
It is **stage-aware**: the required structure differs per stage:

- `propose_candidate` — Recommendation, why it fits, key trade-offs, risks, WAF impact, cost drivers, open decisions, persisted artifacts, next action
- `validate` — Risks, WAF findings, evidence, remediation, persisted artifacts, next action
- `pricing` — Assumptions, cost drivers, confidence, gaps, persisted artifacts, next action
- `iac` — Deployment shape, validation status, operational risks, persisted artifacts, next action
- `clarify` — Questions, default assumptions, impact on architecture

**Key principle**: Artifacts are persisted via AAA tools. The Architect Briefing in chat provides the decision-quality synthesis — not a copy of the persisted content.

Good example: *"I recommend Azure Container Apps because it matches your serverless-first constraint. Key trade-off: less control than AKS. Top risk: cold-start latency — mitigated via min-replicas=2. I persisted candidate CA-001."*

Bad example: *"I created change set X."*


## Structure

```yaml
version: "1.0"
system_prompt: |
  # Main system instructions for the agent

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
from app.agents_system.config.prompt_loader import get_prompt_loader, reload_prompts

# Access prompts (loaded from YAML)
loader = get_prompt_loader()
system_prompt = loader.get_system_prompt()

# Force reload prompts (for hot-reload)
reload_prompts()

# Compose a stage-aware prompt
system_prompt = loader.compose_prompt(
    agent_type="orchestrator",
    stage="clarify",
    context_budget=2000,
)
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
- Missing modular files are allowed; the loader skips them and can fall back to `agent_prompts.yaml`

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
