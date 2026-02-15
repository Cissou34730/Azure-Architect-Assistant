# Multi-Agent Architecture (Moved)

This document has moved to:

- [`docs/architecture/multi-agent-architecture.md`](./architecture/multi-agent-architecture.md)

Keep this file as a compatibility pointer only.

---

**Status**: Active (pointer)  
**Last Updated**: 2026-02-15  
**Owner**: Engineering
agent_handoff_context = {
    "project_context": str,  # Summary of project state
    "requirements": str,  # Extracted requirements
    "nfr_summary": str,  # Non-functional requirements
    "constraints": dict,  # Budget, timeline, compliance
    "previous_decisions": list,  # ADRs and choices made
    "user_request": str,  # Original user message
    "routing_reason": str,  # Why this agent was selected
}
```

---

## Routing Rules

### Rule 1: Route to Architecture Planner

**Conditions:**
```python
def should_route_to_architecture_planner(state: GraphState) -> bool:
    last_message = state["messages"][-1].content.lower()
    
    # Explicit architecture keywords
    arch_keywords = [
        "architecture", "design the architecture", "propose architecture",
        "candidate architecture", "architecture proposal", "system design",
        "how should i architect"
    ]
    if any(kw in last_message for kw in arch_keywords):
        return True
    
    # Project stage suggests architecture needed
    if state.get("next_stage") == "propose_candidate":
        return True
    
    # Complexity threshold
    project_context = state.get("context_summary", "")
    complexity_indicators = [
        "multi-region", "high availability", "disaster recovery",
        "compliance", "SOC 2", "HIPAA", "GDPR",
        "microservices", "event-driven", "real-time"
    ]
    complexity_count = sum(1 for ind in complexity_indicators if ind in project_context.lower())
    if complexity_count >= 3:
        return True
    
    return False
```

**Handoff Context Preparation:**
```python
handoff_context = {
    "project_context": state.get("context_summary", ""),
    "requirements": extract_requirements(state),
    "nfr_summary": extract_nfr(state),
    "constraints": extract_constraints(state),
    "previous_decisions": state.get("current_project_state", {}).get("adrs", []),
    "user_request": state["messages"][-1].content,
    "routing_reason": "Complex architecture design required with NFR analysis",
}
```

---

### Rule 2: Route to IaC Generator

**Conditions:**
```python
def should_route_to_iac_generator(state: GraphState) -> bool:
    last_message = state["messages"][-1].content.lower()
    
    # Explicit IaC keywords
    iac_keywords = [
        "terraform", "bicep", "iac", "infrastructure as code",
        "infrastructure code", "deploy", "provision"
    ]
    if any(kw in last_message for kw in iac_keywords):
        # Only route if architecture is finalized
        project_state = state.get("current_project_state", {})
        has_architecture = bool(project_state.get("candidateArchitectures"))
        return has_architecture
    
    # Project stage is IaC
    if state.get("next_stage") == "iac":
        return True
    
    return False
```

**Handoff Context Preparation:**
```python
handoff_context = {
    "project_context": state.get("context_summary", ""),
    "architecture": state.get("current_project_state", {}).get("candidateArchitectures", [])[0],
    "resource_list": extract_azure_resources(state),
    "constraints": extract_constraints(state),
    "iac_format": detect_iac_format(state["messages"][-1].content),  # "bicep" or "terraform"
    "user_request": state["messages"][-1].content,
    "routing_reason": "IaC generation for finalized architecture",
}
```

---

### Rule 3: Route to Main Agent (Default)

**Conditions:**
```python
def should_route_to_main_agent(state: GraphState) -> bool:
    # Default if no specialized agent matches
    return not (
        should_route_to_architecture_planner(state) or
        should_route_to_iac_generator(state)
    )
```

---

## Implementation Strategy

### Phase 2.1: Architecture Planner (Week 1)

1. **Create Architecture Planner Prompt** (`architecture_planner_prompt.yaml`)
   - Extract architecture design sections from main prompt
   - Add NFR analysis methodology
   - Add C4 diagram guidelines
   - Add target-first delivery strategy

2. **Implement Architecture Planner Node** (`nodes/architecture_planner.py`)
   - Load specialized prompt
   - Create MCPReActAgent with architecture tools
   - Handle handoff context
   - Return structured proposal

3. **Enhance Routing Logic** (`nodes/stage_routing.py`)
   - Add `should_route_to_architecture_planner()` function
   - Prepare handoff context with NFR extraction
   - Add logging for routing decisions

4. **Update Graph Factory** (`graph_factory.py`)
   - Add architecture_planner node
   - Add conditional edge from router to architecture_planner
   - Handle sub-agent errors with fallback

---

### Phase 2.2: IaC Generator (Week 2)

1. **Create IaC Generator Prompt** (`iac_generator_prompt.yaml`)
   - Extract IaC sections from main prompt
   - Add Bicep best practices
   - Add Terraform best practices
   - Add schema validation requirements

2. **Implement IaC Generator Node** (`nodes/iac_generator.py`)
   - Load specialized prompt
   - Create MCPReActAgent with Bicep/Terraform tools
   - Handle handoff context
   - Return validated IaC code

3. **Enhance Routing Logic** (`nodes/stage_routing.py`)
   - Add `should_route_to_iac_generator()` function
   - Validate architecture exists before routing
   - Add logging for routing decisions

4. **Update Graph Factory** (`graph_factory.py`)
   - Add iac_generator node
   - Add conditional edge from router to iac_generator
   - Handle sub-agent errors with fallback

---

### Phase 2.3: Main Agent Simplification (Week 3)

1. **Reduce Main Prompt** (`agent_prompts.yaml`)
   - Remove architecture design sections (~80 lines)
   - Remove IaC generation sections (~80 lines)
   - Add delegation instructions for sub-agents
   - Update version to 1.2
   - Target: 220-240 lines (from 351)

2. **Add Delegation Guidance**
   ```yaml
   **When to Delegate to Sub-Agents:**
   
   1. **Architecture Planner** - Delegate when:
      - User asks for architecture design, proposal, or candidate
      - Complex NFR analysis required (multi-region, HA, DR, compliance)
      - C4 diagrams needed
      - Phased delivery planning requested
   
   2. **IaC Generator** - Delegate when:
      - User asks for Terraform or Bicep code
      - Architecture is finalized and ready for implementation
      - IaC validation or migration needed
   
   Your role: Clarify requirements, detect intent, prepare handoff context.
   Sub-agents will handle specialized execution.
   ```

3. **Test Delegation**
   - Verify routing works correctly
   - Test handoff context preparation
   - Validate no regression in main agent capabilities

---

## Testing Strategy

### Unit Tests

1. **Routing Logic Tests** (`tests/test_multi_agent_routing.py`)
   ```python
   def test_route_to_architecture_planner_explicit_keyword():
       state = {"messages": [HumanMessage(content="Design the architecture")]}
       assert should_route_to_architecture_planner(state) == True
   
   def test_route_to_iac_generator_with_architecture():
       state = {
           "messages": [HumanMessage(content="Generate Bicep code")],
           "current_project_state": {"candidateArchitectures": [...]},
       }
       assert should_route_to_iac_generator(state) == True
   
   def test_route_to_main_agent_general_question():
       state = {"messages": [HumanMessage(content="What is Azure App Service?")]}
       assert should_route_to_main_agent(state) == True
   ```

2. **Handoff Context Tests** (`tests/test_handoff_context.py`)
   ```python
   def test_handoff_context_includes_nfr():
       state = {...}
       context = prepare_handoff_context(state, "architecture_planner")
       assert "nfr_summary" in context
       assert "requirements" in context
   ```

---

### Integration Tests

1. **E2E Architecture Request** (`tests/e2e/test_architecture_planner_e2e.py`)
   ```python
   async def test_architecture_planner_generates_complete_proposal():
       # Given: Project with requirements
       project_id = create_test_project(requirements={"sla": "99.9%", "scale": "1M users"})
       
       # When: User requests architecture
       response = await send_message(project_id, "Design the target architecture")
       
       # Then: Architecture Planner generates complete proposal
       assert "System Context Diagram" in response
       assert "Container Diagram" in response
       assert "NFR Analysis" in response
       assert "[Target Architecture]" in response
   ```

2. **E2E IaC Generation** (`tests/e2e/test_iac_generator_e2e.py`)
   ```python
   async def test_iac_generator_produces_valid_bicep():
       # Given: Project with finalized architecture
       project_id = create_test_project_with_architecture()
       
       # When: User requests Bicep code
       response = await send_message(project_id, "Generate Bicep code for this architecture")
       
       # Then: IaC Generator produces valid Bicep
       assert "resource " in response  # Bicep resource syntax
       assert extract_bicep_code(response)  # Extractable code block
   ```

---

### Regression Tests

1. **Main Agent Still Works** (`tests/test_main_agent_regression.py`)
   ```python
   async def test_main_agent_handles_general_questions():
       response = await send_message(project_id, "What is Azure SQL Database?")
       assert "Azure SQL Database" in response
       assert routing_decision["agent"] == "main"
   ```

2. **No Breaking Changes** (`tests/test_no_breaking_changes.py`)
   - Run all existing E2E tests
   - Verify golden outputs still match (or update if improved)
   - Check database persistence still works

---

## Metrics and Success Criteria

### Prompt Complexity Reduction

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Main Agent Prompt Size | 351 lines | ~220-240 lines | ≤250 lines |
| Architecture Planner Prompt | N/A | ~80 lines | ≤100 lines |
| IaC Generator Prompt | N/A | ~80 lines | ≤100 lines |
| **Total System Prompt Size** | 351 lines | ~380-400 lines | Acceptable for specialization |

**Rationale:** Total size increases slightly, but each prompt is focused and maintainable. Main agent complexity reduced by 31%.

---

### Routing Accuracy

| Scenario | Expected Agent | Accuracy Target |
|----------|---------------|-----------------|
| "Design the architecture" | Architecture Planner | 100% |
| "Generate Bicep code" | IaC Generator | 100% |
| "What is Azure SQL?" | Main Agent | 100% |
| Complex architecture (multi-region, HA, compliance) | Architecture Planner | ≥90% |
| General question | Main Agent | ≥95% |

---

### Quality Metrics

| Metric | Target |
|--------|--------|
| Architecture Planner: NFR analysis completeness | 100% (all 5 dimensions) |
| Architecture Planner: Diagram syntax validity | 100% (valid Mermaid) |
| IaC Generator: Bicep lint pass rate | ≥95% |
| IaC Generator: Schema validation pass rate | 100% |
| E2E test pass rate | 100% (no regressions) |

---

## Rollout Plan

### Week 1: Architecture Planner
- Day 1-2: Create prompt and node implementation
- Day 3: Integrate routing logic and update graph
- Day 4: Unit tests and integration tests
- Day 5: E2E testing and refinement

### Week 2: IaC Generator
- Day 1-2: Create prompt and node implementation
- Day 3: Integrate routing logic and update graph
- Day 4: Unit tests and integration tests
- Day 5: E2E testing and refinement

### Week 3: Main Agent Simplification
- Day 1: Reduce main prompt size
- Day 2: Add delegation instructions
- Day 3: Regression testing
- Day 4: Documentation updates
- Day 5: Final validation and deployment

---

## Risk Mitigation

### Risk 1: Routing Errors
**Mitigation:**
- Extensive unit tests for routing logic
- Fallback to main agent on uncertainty
- Logging all routing decisions for analysis

### Risk 2: Context Loss Between Agents
**Mitigation:**
- Comprehensive handoff context structure
- State persistence between nodes
- Validation tests for context completeness

### Risk 3: Sub-Agent Failures
**Mitigation:**
- Graceful error handling with fallback
- Main agent can complete task if sub-agent fails
- Detailed error logging for debugging

### Risk 4: Regression in Main Agent
**Mitigation:**
- Run full test suite before/after changes
- Golden output validation
- Gradual rollout with monitoring

---

## Future Enhancements (Post-Phase 2)

1. **More Specialized Agents**
   - Validation Specialist (WAF checks, security analysis)
   - Pricing Specialist (cost estimation, TCO analysis)
   - ADR Specialist (architecture decision documentation)

2. **Agent Collaboration**
   - Multi-agent conversations (Architecture Planner ↔ IaC Generator)
   - Iterative refinement based on feedback

3. **Learning from Usage**
   - Track routing accuracy over time
   - Adjust routing thresholds based on user satisfaction
   - A/B testing for prompt variations

---

## Appendix A: File Changes Summary

### New Files
- `backend/config/prompts/architecture_planner_prompt.yaml` (~80 lines)
- `backend/config/prompts/iac_generator_prompt.yaml` (~80 lines)
- `backend/app/agents_system/langgraph/nodes/architecture_planner.py` (~150 lines)
- `backend/app/agents_system/langgraph/nodes/iac_generator.py` (~150 lines)
- `tests/test_multi_agent_routing.py` (~200 lines)
- `tests/test_handoff_context.py` (~100 lines)
- `tests/e2e/test_architecture_planner_e2e.py` (~150 lines)
- `tests/e2e/test_iac_generator_e2e.py` (~150 lines)

### Modified Files
- `backend/config/prompts/agent_prompts.yaml` (351 → ~230 lines)
- `backend/app/agents_system/langgraph/state.py` (+5 fields)
- `backend/app/agents_system/langgraph/graph_factory.py` (+2 nodes, +2 conditional edges)
- `backend/app/agents_system/langgraph/nodes/stage_routing.py` (+100 lines routing logic)
- `docs/SYSTEM_ARCHITECTURE.md` (add multi-agent section)
- `docs/AGENT_ENHANCEMENT_IMPLEMENTATION_PLAN.md` (mark Phase 2 complete)
- `CHANGELOG.md` (add [1.2.0] entry)

---

## Appendix B: Prompt Size Breakdown

### Main Agent Prompt (Target: 220-240 lines)
```yaml
1. Role & Identity               (~20 lines)
2. Behavior Rules                (~30 lines)
3. Workload Classification       (~15 lines)
4. Requirement Clarification     (~40 lines, includes Ask Before Assuming)
5. Tools & MCP Strategy          (~40 lines)
6. Output Structure              (~30 lines, simplified)
7. Guardrails                    (~20 lines)
8. Delegation Instructions       (~25 lines, NEW)

Total: ~220 lines
```

### Architecture Planner Prompt (Target: ~80 lines)
```yaml
1. Role & Expertise              (~10 lines)
2. Input/Output Specification    (~10 lines)
3. Methodology                   (~40 lines)
   - Target architecture first
   - NFR-driven design
   - C4 diagrams
   - Functional flows
   - Optional MVP
4. Available Tools               (~10 lines)
5. Guardrails                    (~10 lines)

Total: ~80 lines
```

### IaC Generator Prompt (Target: ~80 lines)
```yaml
1. Role & Expertise              (~10 lines)
2. Input/Output Specification    (~10 lines)
3. Methodology                   (~40 lines)
   - Bicep best practices
   - Terraform best practices
   - Schema validation
   - Parameterization
   - Modularization
4. Available Tools               (~10 lines)
5. Guardrails                    (~10 lines)

Total: ~80 lines
```

---

**Document Status:** ✅ Complete - Ready for Implementation

**Next Steps:**
1. Implement Architecture Planner (Task 2.2)
2. Implement IaC Generator (Task 2.3)
3. Reduce Main Agent Prompt (Task 2.4)
4. Test and Document (Tasks 2.5-2.6)
