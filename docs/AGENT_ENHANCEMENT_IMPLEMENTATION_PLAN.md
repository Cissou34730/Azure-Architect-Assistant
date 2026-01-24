# AAA Agent Enhancement - Implementation Plan

**Date:** January 24, 2026  
**Objective:** Implement recommendations from Agent Review to achieve enterprise-grade architecture assistant quality  
**Strategy:** Decompose complexity from main prompt into specialized sub-agents

---

## Overview

This plan implements the recommendations from [AGENT_REVIEW_AND_RECOMMENDATIONS.md](./AGENT_REVIEW_AND_RECOMMENDATIONS.md) in three phases:

1. **Phase 1: Refactor & Conservative Enhancement** (Main Prompt) - 1 week
2. **Phase 2: Multi-Agent Decomposition** (Architecture Planner + IaC Generator) - 2-3 weeks
3. **Phase 3: Optional Specialized Agents** (SaaS Advisor + Cost Estimator) - 2 weeks

**Total Estimated Timeline:** 5-6 weeks

---

## Phase 1: Refactor & Conservative Enhancement (Main Prompt)

**Duration:** 1 week  
**Goal:** Improve main agent behavior without bloating the prompt further

### Prerequisites
- [x] Agent review completed
- [x] User feedback incorporated
- [ ] Create feature branch: `feature/agent-prompt-refactor`
- [ ] Backup current prompt: `agent_prompts.yaml.backup-2026-01-24`

---

### Task 1.1: Analyze & Refactor Current Prompt

**Objective:** Reduce redundancy and improve clarity in existing 357-line prompt before adding new content.

**Steps:**

1. **Read current prompt structure**
   ```bash
   # Open current prompt
   code backend/config/prompts/agent_prompts.yaml
   ```

2. **Identify redundant sections**
   - [ ] Check for duplicate WAF pillar instructions
   - [ ] Identify repetitive tool usage guidance
   - [ ] Find overlapping behavior rules
   - [ ] Mark sections that can be moved to sub-agents later

3. **Consolidate without changing behavior**
   - [ ] Merge "Behavior Rules" subsections if overlapping
   - [ ] Combine "Available Tools" and tool-specific sections
   - [ ] Simplify "Stage-Driven Behavior" to reference list only
   - [ ] Remove verbose examples if covered in few-shot section

4. **Create refactored draft**
   - [ ] Target: Reduce from 357 lines to ~300 lines
   - [ ] Preserve all functional behavior
   - [ ] Use YAML anchors/aliases for repeated patterns if applicable

**Acceptance Criteria:**
- Prompt is 10-15% shorter
- No functionality removed, only consolidated
- All existing E2E tests pass (scenario-a, scenario-behavior)

**Estimated Effort:** 4-6 hours

---

### Task 1.2: Add MCP-First Documentation Strategy

**Objective:** Emphasize MCP tools over direct web search with precise query guidance.

**File:** `backend/config/prompts/agent_prompts.yaml`

**Location:** Update existing section "5. Available Tools"

**Changes:**

```yaml
**5. Available Tools & Documentation Search Strategy (MCP-First)**

**Primary Documentation Tools (ALWAYS use these):**
- **microsoft_docs_search**: Semantic search of Microsoft/Azure documentation via MCP
  - CONSTRUCT PRECISE QUERIES: Include service name + specific feature
  - Example: "Azure SQL Database Private Link configuration" NOT "SQL security"
  - Use for: Architecture patterns, service-specific guidance, best practices
  
- **microsoft_code_sample_search**: Find official Microsoft code examples via MCP
  - CONSTRUCT PRECISE QUERIES: Include SDK name + language + specific API
  - Example: "Azure Storage Blob Python upload async" NOT "storage code"
  - Use for: Implementation examples, SDK usage, API patterns
  
- **microsoft_docs_fetch**: Fetch complete documentation page as markdown via MCP
  - Use when: Search results reference specific high-value page
  - Use for: Complete tutorials, detailed configuration guides

- **kb_search**: Search curated Azure knowledge bases (WAF, CAF)
  - Use FIRST for: Architecture principles, framework guidance
  - Returns: Cited answers from curated sources

**CRITICAL RULES:**
- NEVER suggest external web search engines or generic web queries
- NEVER say "search the web" or "look online"
- If MCP tools don't have answer, state "This information is not available in Microsoft documentation" and ask user to clarify or provide documentation
- ALL recommendations MUST cite Microsoft Learn URLs: [Service Name](https://learn.microsoft.com/...)

**Key Documentation URLs to Reference:**
- WAF Overview: https://learn.microsoft.com/azure/well-architected/
- WAF Security: https://learn.microsoft.com/azure/well-architected/security/
- WAF Reliability: https://learn.microsoft.com/azure/well-architected/reliability/
- WAF Cost: https://learn.microsoft.com/azure/well-architected/cost/
- WAF Performance: https://learn.microsoft.com/azure/well-architected/performance-efficiency/
- WAF Operations: https://learn.microsoft.com/azure/well-architected/operational-excellence/
- Azure Architecture Center: https://learn.microsoft.com/azure/architecture/
```

**Steps:**
1. [ ] Locate "5. Available Tools" section
2. [ ] Replace with enhanced MCP-first version above
3. [ ] Update react_template to emphasize MCP tool usage
4. [ ] Add to few-shot examples: Example of precise vs vague MCP query

**Validation:**
- [ ] Test agent with query: "How do I secure my database?" → Should use microsoft_docs_search with precise query
- [ ] Verify agent never suggests "search the web"
- [ ] Check citations include Microsoft Learn URLs

**Estimated Effort:** 2-3 hours

---

### Task 1.3: Add "Ask Before Assuming" Checklist

**Objective:** Ensure agent asks for critical requirements instead of making assumptions.

**File:** `backend/config/prompts/agent_prompts.yaml`

**Location:** Enhance section "2.A. Always Clarify & Challenge"

**Changes:**

```yaml
**2. Behavior Rules**

A. **Always Clarify & Challenge (Ask Before Assuming)**

**Critical Requirements Checklist:**
Before making architectural recommendations, verify these critical aspects are known. If ANY are unclear, ASK SPECIFICALLY:

Required Information:
- [ ] **Performance & Scale:** SLA targets (uptime %), RTO/RPO, expected load (requests/sec, data volume), growth projections (1 year, 3 year)
- [ ] **Security & Compliance:** Regulatory frameworks (GDPR, HIPAA, SOC 2, PCI DSS), data residency requirements, industry-specific regulations
- [ ] **Budget & Cost:** CapEx vs OpEx preference, monthly/annual budget constraints, cost optimization priorities
- [ ] **Operations:** Team DevOps maturity (none/basic/advanced), monitoring capabilities, on-call support model, maintenance windows
- [ ] **Integration:** Existing systems to integrate with, legacy constraints, authentication/identity systems, migration requirements
- [ ] **Data:** Volume (GB/TB), velocity (transactions/sec), variety (structured/unstructured), retention requirements
- [ ] **Users:** Geographic distribution, concurrent users, authentication model (internal/external), access patterns

**Asking Strategy:**
- Group related questions (max 5 per response)
- Explain WHY the information affects architecture decisions
- Provide examples: "For example, if you need 99.99% uptime, we'll need multi-region deployment"

**Challenge When:**
- User proposes single-region for high-availability requirements
- User suggests manual operations for high-scale scenarios  
- User omits security for compliance-driven workloads
- User choice contradicts technical feasibility or cost-efficiency
- Design introduces high risk without acknowledging trade-offs

You are NOT a passive assistant; you are an Architect. Challenge the user if their choice introduces high risk.
```

**Steps:**
1. [ ] Locate "2.A. Always Clarify & Challenge" section
2. [ ] Replace with checklist version above
3. [ ] Update few-shot examples to demonstrate asking grouped questions
4. [ ] Add example of challenging user's risky assumption

**Validation:**
- [ ] Test with vague requirement: "Build me a web app" → Agent asks for checklist items
- [ ] Test with risky choice: "Single region is fine" → Agent challenges if HA required
- [ ] Verify questions are grouped (not one-by-one)

**Estimated Effort:** 2 hours

---

### Task 1.4: Add Target Architecture + Optional MVP Path

**Objective:** Always provide complete target architecture first, with MVP as optional path only when requested.

**File:** `backend/config/prompts/agent_prompts.yaml`

**Location:** Replace section "9. Stage-Driven Behavior" with updated version

**Changes:**

```yaml
**9. Target Architecture Delivery Strategy**

**PRIMARY OUTPUT: Always provide complete TARGET ARCHITECTURE first.**

Your architecture proposal MUST start with the full production-ready design:

**Target Architecture (Mandatory):**
1. **Complete Design** - Full production-ready architecture
   - All required Azure services with proper sizing/SKUs
   - Multi-region setup if needed for SLA/DR requirements
   - Complete security controls (WAF Security pillar: identity, network, data encryption, threat protection)
   - Complete reliability features (WAF Reliability pillar: HA, DR, backup, monitoring)
   - Full automation readiness (IaC-compatible, CI/CD-ready)
   - Performance optimization (caching, CDN, auto-scaling)
   - Cost optimization (reserved instances, right-sizing recommendations)
   - Label all diagrams: **[Target Architecture]**

2. **NFR Alignment Statement**
   - Explicitly state how target architecture meets each NFR
   - "This architecture achieves 99.95% SLA through [multi-region deployment + Azure Front Door failover]"
   - "Security compliance [GDPR] achieved through [data residency + encryption + audit logging]"

**Optional MVP Path (Only When Requested):**
- AFTER presenting target architecture, ASK: "Would you like me to also propose a simplified MVP path for faster initial delivery?"
- Only provide if user confirms interest
- MVP defers complexity, does NOT remove requirements:
  - ✅ MVP: Single-region, manual failover, basic monitoring
  - ❌ NOT MVP: Removing security, skipping compliance, ignoring scale requirements

**MVP Simplifications (when requested):**
- Deployment: Single region → Multi-region in Phase 2
- Operations: Manual processes → Full automation in Phase 2
- Integration: REST/synchronous → Event-driven in Phase 2
- Monitoring: Basic metrics → Advanced observability in Phase 2
- Label diagrams: **[Phase 1 - MVP]** vs **[Target Architecture]**

**Migration Path (if MVP provided):**
For each deferred feature, specify:
- What changes in Phase 2 (components to add, configurations to update)
- Zero-downtime transition approach (blue-green, rolling update)
- Data migration strategy if applicable
- Estimated effort for transition
- Rollback plan if transition fails

**Stage-Driven Workflow (updated):**
1. Clarify requirements (use checklist from section 2.A)
2. **Propose TARGET architecture** (full design with NFR alignment)
3. Offer optional MVP path if user requests faster delivery
4. Make decisions (ADRs) → persist via aaa_manage_adr
5. Validate vs WAF + risks → persist via aaa_record_validation_results
6. Cost baseline (if requested) → persist via aaa_record_iac_and_cost
7. IaC generation (if requested) → persist via aaa_record_iac_and_cost
8. Export → aaa_export_state

**IMPORTANT:** 
- Never assume user wants MVP - always show target architecture first
- MVP is an OPTION for phased delivery, not a replacement for proper design
- Human architect can skip MVP entirely and implement target directly
```

**Steps:**
1. [ ] Locate "9. Stage-Driven Behavior" section
2. [ ] Replace with Target Architecture strategy above
3. [ ] Update few-shot examples to show target architecture presentation
4. [ ] Add example of offering MVP after target architecture

**Validation:**
- [ ] Test with complex requirement → Agent shows full target architecture first
- [ ] Verify MVP is only offered as question, not default
- [ ] Check NFR alignment statement is explicit

**Estimated Effort:** 3-4 hours

---

### Task 1.5: Add C4 + Functional Flow Diagram Requirements

**Objective:** Require both technical (C4) and business perspective (functional flow) diagrams.

**File:** `backend/config/prompts/agent_prompts.yaml`

**Location:** Update section "7. Output Structure - B. Diagrams"

**Changes:**

```yaml
**7. Output Structure**

B. **Diagrams (C4 Model + Functional Flows)**

Generate Mermaid diagrams that are:
- Syntactically valid (test before including)
- Reflecting only validated decisions (no assumptions)
- **Balanced between technical and business perspectives**

**C4 Diagrams (Technical Architecture Perspective):**

1. **System Context Diagram** (Mandatory for all projects)
   - Shows: System boundary, external actors (users, external systems), high-level interactions
   - Purpose: Understand system's place in broader ecosystem
   - Audience: All stakeholders (technical + non-technical)

2. **Container Diagram** (Mandatory for all projects)
   - Shows: Major Azure services, data stores, APIs, data flows between containers
   - Purpose: High-level technology choices and communication patterns
   - Audience: Architects, technical leads

3. **Component Diagram** (Optional, only when requested or highly complex)
   - Shows: Internal structure of a specific container
   - Purpose: Detailed design within a service
   - Audience: Developers, detailed design reviews

**Functional Flow Diagrams (Business Perspective):**

4. **User Journey Flows** (Mandatory for user-facing systems)
   - Shows: End-to-end user workflows (authentication → core transaction → result)
   - Purpose: Validate business process against technical design
   - Examples: "Customer places order", "User authenticates and accesses dashboard"
   - Use: Sequence diagram (Mermaid) showing user ↔ system interactions
   - Audience: Product managers, business stakeholders, UX designers

5. **Business Process Flows** (For complex business logic)
   - Shows: Multi-step business processes with decision points
   - Purpose: Ensure technical architecture supports business requirements
   - Examples: "Order fulfillment process", "Payment processing workflow"
   - Use: Flowchart (Mermaid) showing decision trees and process steps
   - Audience: Business analysts, domain experts

6. **Cross-System Integration Flows** (For enterprise integrations)
   - Shows: How multiple systems interact for business outcomes
   - Purpose: Validate integration patterns and data flows
   - Examples: "CRM to ERP synchronization", "Partner API integration"
   - Use: Sequence diagram showing system-to-system communication
   - Audience: Integration architects, API developers

**Diagram Generation Rules:**
- MUST use Mermaid syntax (no PlantUML unless explicitly requested)
- MUST label diagram type in heading: "## System Context Diagram [Target Architecture]"
- MUST use clear node labels (avoid abbreviations: "API Gateway" not "APIGW")
- MUST show directional relationships with labeled arrows
- For target architecture vs MVP: Generate diagrams for BOTH if MVP path requested

**Diagram Explanation (Mandatory for Each Diagram):**

Each diagram MUST include:

1. **Purpose:** One sentence - what this diagram shows
2. **Key Elements:** List and explain major components/actors (3-5 items)
3. **Relationships:** How components interact (protocols, patterns)
4. **NFR Alignment:** How this design addresses non-functional requirements:
   - **Scalability:** How components scale (horizontal/vertical, auto-scaling configuration)
   - **Performance:** Latency targets, throughput capacity, caching strategy
   - **Security:** Authentication/authorization, network boundaries, encryption (at rest/in transit)
   - **Reliability:** HA configuration, failover mechanisms, RTO/RPO how achieved
   - **Maintainability:** Update strategy, versioning approach, operational complexity
5. **Trade-offs:** Explicit statement of what was sacrificed (e.g., "Higher cost for better availability")
6. **Assumptions:** Any assumptions made (e.g., "Assumes < 1000 concurrent users")

**Example NFR Analysis for System Context Diagram:**
```
### NFR Analysis

**Scalability:** Azure Front Door distributes load globally. API Management can scale to 50+ units. Backend containers auto-scale based on CPU (70% threshold).

**Performance:** CDN reduces latency to < 50ms for static content. API Gateway caching provides 80% cache hit rate. Target: 95th percentile response time < 500ms.

**Security:** All external traffic via Azure Front Door with WAF. API Management enforces OAuth 2.0. Backend in private VNET. Encryption: TLS 1.3 in transit, AES-256 at rest.

**Reliability:** Multi-region active-active. Front Door detects backend failures in < 30s and routes to healthy region. Target: 99.95% SLA (RTO=30s, RPO=5min).

**Maintainability:** Blue-green deployment via slot swap. API versioning allows backward compatibility. Centralized logging in Log Analytics.

**Trade-offs:** Multi-region increases cost by 80% but achieves required 99.95% SLA. Complexity of managing two active regions.
```
```

**Steps:**
1. [ ] Locate "7. Output Structure" section, subsection B
2. [ ] Replace with C4 + Functional Flow version above
3. [ ] Add to few-shot examples: Example of System Context diagram with full NFR analysis
4. [ ] Add example of User Journey Flow diagram

**Validation:**
- [ ] Test complex scenario → Agent generates C4 diagrams + user journey
- [ ] Verify each diagram has complete NFR analysis
- [ ] Check diagrams are labeled with architecture phase

**Estimated Effort:** 3-4 hours

---

### Task 1.6: Test Phase 1 Changes

**Objective:** Validate all prompt enhancements work correctly without regressions.

**Test Plan:**

1. **Regression Testing**
   ```bash
   # Run existing E2E tests
   uv run python scripts/e2e/aaa_e2e_runner.py --scenario scenario-a --in-process
   uv run python scripts/e2e/aaa_e2e_runner.py --scenario scenario-behavior --in-process
   ```
   - [ ] scenario-a passes
   - [ ] scenario-behavior passes
   - [ ] Advisory quality scores maintain ≥4/8 average

2. **MCP-First Testing**
   - [ ] Test query: "How do I secure Azure SQL?" → Agent uses microsoft_docs_search with precise query
   - [ ] Verify no "search the web" suggestions
   - [ ] Check all recommendations have Microsoft Learn URLs

3. **Ask Before Assuming Testing**
   - [ ] Test vague input: "Build an e-commerce platform" → Agent asks checklist questions
   - [ ] Verify questions are grouped (max 5 per response)
   - [ ] Check agent explains WHY information is needed

4. **Target Architecture Testing**
   - [ ] Test complex requirement → Agent presents full target architecture first
   - [ ] Verify MVP is only offered as question after target
   - [ ] Check NFR alignment statement is explicit and detailed

5. **C4 + Functional Flow Testing**
   - [ ] Test user-facing system → Agent generates System Context + User Journey
   - [ ] Verify each diagram has NFR analysis section
   - [ ] Check diagrams are properly labeled

6. **Challenge Behavior Testing**
   - [ ] Test risky choice: "Let's use single region" for 99.99% SLA requirement
   - [ ] Verify agent challenges with alternatives and trade-offs

**Create New E2E Scenario (Optional but Recommended):**

Create `scripts/e2e/scenarios/scenario-target-architecture/` to validate new behavior:
- Complex RFP (multi-region, compliance-driven, high-scale)
- Should trigger: Target architecture generation + NFR analysis + functional flows
- Should NOT: Default to MVP without asking

**Acceptance Criteria:**
- [ ] All existing tests pass
- [ ] No regression in advisory quality scores
- [ ] All 6 validation tests pass
- [ ] Manual review of 2-3 agent responses confirms quality improvement

**Estimated Effort:** 1 day

---

### Task 1.7: Document Phase 1 Changes

**Objective:** Update documentation to reflect prompt enhancements.

**Files to Update:**

1. **backend/config/prompts/README.md**
   - [ ] Update "Key Changes" section with Phase 1 enhancements
   - [ ] Add MCP-first documentation strategy explanation
   - [ ] Add target architecture + optional MVP guidance
   - [ ] Update version to 1.1

2. **docs/SYSTEM_ARCHITECTURE.md**
   - [ ] Update "Agent Behavior" section with new strategy
   - [ ] Add diagram standards (C4 + functional flows)

3. **CHANGELOG.md** (create if doesn't exist)
   ```markdown
   ## [1.1.0] - 2026-01-XX

   ### Enhanced
   - **MCP-First Documentation:** Emphasize precise MCP queries, never suggest web search
   - **Target Architecture Primary:** Always provide complete target architecture, MVP optional
   - **Ask Before Assuming:** Added critical requirements checklist for requirement gathering
   - **C4 + Functional Flows:** Require both technical and business perspective diagrams
   - **NFR Analysis:** Mandatory NFR analysis for every diagram with explicit trade-offs

   ### Refactored
   - Consolidated redundant sections in agent_prompts.yaml
   - Reduced prompt complexity while preserving functionality
   ```

**Estimated Effort:** 2 hours

---

### Phase 1 Summary

**Total Effort:** 5-6 days

**Deliverables:**
- ✅ Refactored agent_prompts.yaml (300 lines, down from 357)
- ✅ MCP-first documentation strategy
- ✅ Ask before assuming checklist
- ✅ Target architecture + optional MVP
- ✅ C4 + functional flow diagram requirements
- ✅ All tests passing
- ✅ Documentation updated

**Next Phase Readiness:**
- [ ] Phase 1 fully tested and validated
- [ ] Team trained on new prompt capabilities
- [ ] User feedback collected on improved behavior

---

## Phase 2: Multi-Agent Decomposition (Architecture Planner + IaC Generator)

**Duration:** 2-3 weeks  
**Goal:** Move specialized logic out of main prompt into dedicated sub-agents

### Prerequisites
- [x] Phase 1 complete and validated
- [ ] Create feature branch: `feature/multi-agent-architecture`
- [ ] Review LangGraph documentation
- [ ] Review current orchestrator code: `backend/app/agents_system/langgraph/`

---

### Task 2.1: Design Multi-Agent Architecture

**Objective:** Define LangGraph architecture with conditional routing to sub-agents.

**Steps:**

1. **Document Current LangGraph Flow**
   ```bash
   # Analyze current graph structure
   find backend/app/agents_system/langgraph -name "*.py" | xargs grep -l "def.*node"
   ```
   - [ ] Map existing nodes: research, stage_routing, postprocess
   - [ ] Identify where sub-agents should be inserted
   - [ ] Document current state schema

2. **Design New Graph Structure**
   
   Create: `docs/MULTI_AGENT_ARCHITECTURE.md`
   
   ```markdown
   # Multi-Agent LangGraph Architecture
   
   ## Graph Flow
   
   ```mermaid
   graph TD
       Start[User Input] --> Research[Research Node]
       Research --> Router[Stage Router]
       Router --> |Stage: Architecture Planning| ArchPlanner[Architecture Planner Agent]
       Router --> |Stage: IaC Generation| IaCGen[IaC Generator Agent]
       Router --> |Default| MainAgent[Main AAA Agent]
       ArchPlanner --> Validate[Validation Node]
       IaCGen --> Validate
       MainAgent --> Validate
       Validate --> |More Work| Router
       Validate --> |Complete| Postprocess[Postprocess Node]
       Postprocess --> End[Final Answer]
   ```
   
   ## Conditional Routing Rules
   
   **Route to Architecture Planner when:**
   - User requests "architecture proposal" or "candidate architecture"
   - Project stage is "proposal" and user asks "what should architecture look like"
   - Complexity threshold exceeded (>5 Azure services, multi-region, etc.)
   
   **Route to IaC Generator when:**
   - User requests "generate Bicep", "create Terraform", "IaC code"
   - Project stage is "iac" in workflow
   - User explicitly asks for infrastructure code
   
   **Route to Main Agent (default):**
   - All other conversational interactions
   - Requirement clarification
   - ADR creation
   - Validation discussions
   ```

3. **Define State Schema Extensions**
   
   File: `backend/app/agents_system/services/aaa_state_models.py`
   
   - [ ] Add field: `current_agent: Literal["main", "architecture_planner", "iac_generator", "saas_advisor", "cost_estimator"] | None`
   - [ ] Add field: `agent_handoff_context: dict[str, Any]` for passing context between agents
   - [ ] Add field: `routing_decision: dict[str, Any]` for logging why agent was chosen

**Deliverables:**
- [ ] `docs/MULTI_AGENT_ARCHITECTURE.md` created
- [ ] State schema updated
- [ ] Routing logic design reviewed and approved

**Estimated Effort:** 1 day

---

### Task 2.2: Implement Architecture Planner Sub-Agent

**Objective:** Create specialized agent for architecture planning, NFR analysis, and diagram generation.

#### Task 2.2.1: Create Architecture Planner Prompt

**File:** Create `backend/config/prompts/architecture_planner_prompt.yaml`

**Content:**

```yaml
# Architecture Planner Sub-Agent
# Specialized in: Target architecture design, NFR analysis, diagram generation, phased delivery

version: "1.0"
last_updated: "2026-01-24"

system_prompt: |
  **Role**
  You are an Architecture Planner Agent specialized in designing complete Azure architectures with deep NFR analysis.
  You work as part of the AAA agent system. The main agent will invoke you when architectural design is needed.

  **Your Expertise:**
  - Target architecture design (complete, production-ready)
  - Non-Functional Requirements (NFR) analysis
  - C4 model diagram generation
  - Functional/business flow diagrams
  - Phased delivery planning (MVP path when requested)
  - Migration path design

  **Input Context**
  You receive from the orchestrator:
  - Project requirements and constraints
  - User's request (e.g., "design the architecture")
  - Current project state (existing decisions, ADRs)
  - NFR requirements (SLA, scale, security, etc.)

  **Your Output**
  You must produce a complete architecture proposal including:
  1. Target Architecture Design (complete, production-ready)
  2. C4 Diagrams (System Context, Container)
  3. Functional Flow Diagrams (user journeys)
  4. NFR Analysis (for each diagram)
  5. Optional MVP Path (only if user requests faster delivery)
  6. Structured proposal ready for aaa_generate_candidate_architecture tool

  **Methodology**

  **1. Target Architecture First (Mandatory)**
  
  Always start with complete target architecture:
  - All required Azure services properly sized
  - Multi-region if needed for SLA/DR
  - Complete security controls (WAF Security pillar)
  - Complete reliability features (WAF Reliability pillar)
  - Performance optimization (caching, CDN, auto-scaling)
  - Cost optimization recommendations
  - Label: [Target Architecture]

  **2. NFR-Driven Design**
  
  For each architectural decision, explicitly address:
  - **Scalability:** How does it scale? (horizontal/vertical, auto-scaling config)
  - **Performance:** Latency targets, throughput, caching strategy
  - **Security:** Authentication, network boundaries, encryption
  - **Reliability:** HA configuration, failover, RTO/RPO achievement
  - **Maintainability:** Update strategy, versioning, operational complexity
  
  **3. C4 Model Diagrams**
  
  Generate in this order:
  1. **System Context Diagram:** System + external actors + boundaries
  2. **Container Diagram:** Azure services + data flows
  3. (Component Diagram only if explicitly requested)

  **4. Functional Flow Diagrams**
  
  For user-facing systems:
  1. **User Journey Flows:** Authentication → core transaction → result
  2. **Business Process Flows:** Multi-step workflows with decisions
  3. **Integration Flows:** Cross-system interactions

  **5. Diagram Requirements**
  
  Every diagram MUST include:
  - Mermaid syntax (syntactically valid)
  - Clear labels (no abbreviations)
  - NFR Analysis section (all 5 dimensions)
  - Trade-offs explicitly stated
  - Assumptions documented

  **6. Optional MVP Path**
  
  After presenting target architecture:
  - ASK: "Would you like a simplified MVP path for faster initial delivery?"
  - Only provide if user confirms
  - MVP defers complexity, doesn't remove requirements
  - Provide clear migration path from MVP to target

  **7. Output Format**
  
  Structure your response:
  
  ```
  # Target Architecture Proposal
  
  ## Executive Summary
  [2-3 sentences: workload type, key services, NFR achievement]
  
  ## Architecture Overview
  [High-level approach and patterns]
  
  ## System Context Diagram [Target Architecture]
  
  ```mermaid
  [diagram]
  ```
  
  ### Explanation
  **Purpose:** [what diagram shows]
  **Key Elements:** [list major components]
  **Relationships:** [how components interact]
  
  ### NFR Analysis
  **Scalability:** [how it scales]
  **Performance:** [latency/throughput targets]
  **Security:** [controls implemented]
  **Reliability:** [HA/DR approach]
  **Maintainability:** [operational considerations]
  **Trade-offs:** [what was sacrificed]
  
  ## Container Diagram [Target Architecture]
  [same structure]
  
  ## User Journey Flow
  [same structure]
  
  ## NFR Achievement Summary
  [Explicit statement of how each NFR is met]
  
  ## Optional: Would you like an MVP path?
  [Ask if user wants simplified delivery approach]
  ```

  **Available Tools**
  You have access to the main agent's tools when needed:
  - microsoft_docs_search (for Azure service references)
  - kb_search (for WAF/CAF patterns)
  
  **Guardrails**
  - NEVER skip NFR analysis
  - NEVER generate diagrams without explanations
  - NEVER provide MVP as default (always ask first)
  - ALWAYS align with WAF pillars
  - ALWAYS cite Microsoft Learn documentation

react_template: |
  [Similar to main agent's react_template but focused on architecture tasks]
  
  You are the Architecture Planner. Generate complete target architecture proposals with NFR analysis.
  
  Question: {input}
  Context: {context}
  
  Thought: [analyze requirements and NFRs]
  Action: [tool name if needed]
  Action Input: [tool input]
  Observation: [result]
  Thought: [continue or complete]
  Final Answer: [complete architecture proposal with diagrams and NFR analysis]
```

**Steps:**
1. [ ] Create file with content above
2. [ ] Review with team for completeness
3. [ ] Add few-shot examples specific to architecture planning

**Estimated Effort:** 1 day

---

#### Task 2.2.2: Implement Architecture Planner Node

**File:** Create `backend/app/agents_system/langgraph/nodes/architecture_planner.py`

**Implementation:**

```python
"""
Architecture Planner Node - Specialized agent for architecture design.
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from app.agents_system.config.prompt_loader import PromptLoader
from app.agents_system.agents.mcp_react_agent import MCPReActAgent
from app.agents_system.services.aaa_state_models import AAAGraphState
from app.agents_system.tools.create_tools import create_aaa_tools

logger = logging.getLogger(__name__)


async def architecture_planner_node(state: AAAGraphState) -> dict[str, Any]:
    """
    Specialized node for architecture planning and diagram generation.
    
    This node is invoked when:
    - User requests architecture proposal
    - Project stage is "proposal" 
    - Complexity threshold exceeded
    
    Args:
        state: Current graph state with project context
        
    Returns:
        Updated state with architecture proposal
    """
    logger.info("🏗️ Architecture Planner Agent activated")
    
    # Load architecture planner prompt
    prompt_loader = PromptLoader()
    arch_planner_prompt = prompt_loader.load_prompt("architecture_planner_prompt.yaml")
    
    # Create agent with architecture planner prompt
    arch_agent = MCPReActAgent(
        system_prompt=arch_planner_prompt["system_prompt"],
        react_template=arch_planner_prompt["react_template"],
        tools=create_aaa_tools(state),  # Reuse AAA tools
        model_name="gpt-4o",  # Use more capable model for complex reasoning
        temperature=0.1,
    )
    
    # Prepare context for architecture planner
    handoff_context = state.get("agent_handoff_context", {})
    project_context = handoff_context.get("project_context", "")
    requirements = handoff_context.get("requirements", "")
    nfr_summary = handoff_context.get("nfr_summary", "")
    
    # Construct input for architecture planner
    arch_planner_input = f"""
{state["messages"][-1].content}

**Context from Main Agent:**
{project_context}

**Requirements:**
{requirements}

**NFR Requirements:**
{nfr_summary}

**Task:** Design the complete target architecture for this project. Include:
1. Target Architecture Design (complete, production-ready)
2. System Context Diagram [Target Architecture]
3. Container Diagram [Target Architecture]
4. User Journey Flow (if user-facing system)
5. NFR Analysis for each diagram
6. After presenting target, ask if user wants MVP path
"""
    
    # Invoke architecture planner agent
    try:
        result = await arch_agent.ainvoke({"input": arch_planner_input})
        arch_proposal = result.get("output", "")
        
        logger.info("✅ Architecture Planner completed")
        
        return {
            "messages": state["messages"] + [AIMessage(content=arch_proposal)],
            "current_agent": "architecture_planner",
            "iterations": state.get("iterations", 0) + 1,
        }
        
    except Exception as exc:
        logger.error(f"❌ Architecture Planner failed: {exc}")
        error_msg = f"Architecture planning failed: {exc!s}. Falling back to main agent."
        return {
            "messages": state["messages"] + [AIMessage(content=error_msg)],
            "current_agent": "main",
            "iterations": state.get("iterations", 0) + 1,
        }
```

**Steps:**
1. [ ] Create file with implementation above
2. [ ] Add error handling and fallback logic
3. [ ] Add logging for debugging
4. [ ] Add unit tests

**Estimated Effort:** 1 day

---

#### Task 2.2.3: Implement Routing Logic for Architecture Planner

**File:** `backend/app/agents_system/langgraph/nodes/stage_routing.py`

**Changes:**

Add routing logic to detect when to invoke architecture planner:

```python
def _should_route_to_architecture_planner(state: AAAGraphState) -> bool:
    """
    Determine if request should go to Architecture Planner sub-agent.
    
    Route to Architecture Planner when:
    - User explicitly requests "architecture", "design", "proposal"
    - Project stage suggests architecture planning needed
    - Complexity indicators detected
    
    Returns:
        True if should route to architecture planner
    """
    last_message = state["messages"][-1].content.lower()
    
    # Explicit architecture request keywords
    arch_keywords = [
        "architecture", "design the architecture", "propose architecture",
        "candidate architecture", "architecture proposal", "system design",
        "how should i architect", "what should the architecture look like"
    ]
    
    if any(keyword in last_message for keyword in arch_keywords):
        logger.info("🎯 Routing to Architecture Planner: explicit request detected")
        return True
    
    # Check project stage
    project_stage = state.get("project_stage")
    if project_stage == "proposal" and ("architecture" in last_message or "design" in last_message):
        logger.info("🎯 Routing to Architecture Planner: proposal stage + design request")
        return True
    
    # Check complexity indicators
    project_context = state.get("agent_handoff_context", {}).get("project_context", "")
    complexity_indicators = [
        "multi-region", "high availability", "disaster recovery",
        "compliance", "SOC 2", "HIPAA", "GDPR",
        "microservices", "event-driven",
    ]
    
    complexity_count = sum(1 for indicator in complexity_indicators if indicator in project_context.lower())
    if complexity_count >= 3:
        logger.info(f"🎯 Routing to Architecture Planner: complexity threshold ({complexity_count} indicators)")
        return True
    
    return False


async def enhanced_stage_routing_node(state: AAAGraphState) -> dict[str, Any]:
    """Enhanced routing with sub-agent support."""
    
    # Check if should route to Architecture Planner
    if _should_route_to_architecture_planner(state):
        return {
            "next_node": "architecture_planner",
            "routing_decision": {
                "agent": "architecture_planner",
                "reason": "Architecture design request detected",
            }
        }
    
    # Check if should route to IaC Generator (implement later)
    # if _should_route_to_iac_generator(state):
    #     return {"next_node": "iac_generator"}
    
    # Default to main agent
    return {
        "next_node": "main_agent",
        "routing_decision": {
            "agent": "main",
            "reason": "Standard conversational interaction",
        }
    }
```

**Steps:**
1. [ ] Add routing detection function
2. [ ] Update stage_routing_node to call detection
3. [ ] Add logging for routing decisions
4. [ ] Add unit tests for routing logic

**Estimated Effort:** 0.5 day

---

#### Task 2.2.4: Update LangGraph to Include Architecture Planner

**File:** `backend/app/agents_system/orchestrator/orchestrator.py` or wherever graph is built

**Changes:**

```python
from app.agents_system.langgraph.nodes.architecture_planner import architecture_planner_node

# In graph construction:
graph_builder = StateGraph(AAAGraphState)

# Add nodes
graph_builder.add_node("research", research_node)
graph_builder.add_node("stage_router", enhanced_stage_routing_node)
graph_builder.add_node("main_agent", main_agent_node)
graph_builder.add_node("architecture_planner", architecture_planner_node)  # NEW
graph_builder.add_node("postprocess", postprocess_node)

# Add conditional edges from router
graph_builder.add_conditional_edges(
    "stage_router",
    lambda state: state.get("next_node", "main_agent"),
    {
        "main_agent": "main_agent",
        "architecture_planner": "architecture_planner",  # NEW
    }
)

# Edges back to validation/postprocess
graph_builder.add_edge("main_agent", "postprocess")
graph_builder.add_edge("architecture_planner", "postprocess")  # NEW
```

**Steps:**
1. [ ] Import architecture_planner_node
2. [ ] Add node to graph
3. [ ] Add conditional routing
4. [ ] Update edges
5. [ ] Test graph compilation

**Estimated Effort:** 0.5 day

---

#### Task 2.2.5: Test Architecture Planner Integration

**Test Plan:**

1. **Unit Tests**
   
   File: `backend/tests/agents_system/test_architecture_planner.py`
   
   ```python
   def test_routing_to_architecture_planner():
       """Test that architecture requests route correctly."""
       state = {
           "messages": [HumanMessage(content="Design the architecture for my app")],
       }
       result = _should_route_to_architecture_planner(state)
       assert result is True
   
   def test_architecture_planner_generates_diagrams():
       """Test that architecture planner generates required diagrams."""
       # Mock state with requirements
       # Invoke architecture_planner_node
       # Assert output contains System Context and Container diagrams
   ```

2. **Integration Tests**
   
   ```bash
   # Test via agent orchestrator
   # Send: "I need to design an e-commerce platform architecture"
   # Expected: Routes to architecture planner, generates target architecture
   ```

3. **E2E Test**
   
   Create new scenario: `scripts/e2e/scenarios/scenario-architecture-planning/`
   - Upload complex RFP
   - Request architecture design
   - Verify: Target architecture generated, diagrams present, NFR analysis included

**Acceptance Criteria:**
- [ ] Routing logic correctly detects architecture requests
- [ ] Architecture planner generates complete proposals
- [ ] Diagrams include NFR analysis
- [ ] Target architecture is always provided first
- [ ] MVP is only offered as question

**Estimated Effort:** 2 days

---

### Task 2.3: Implement IaC Generator Sub-Agent

**Objective:** Create specialized agent for Infrastructure as Code generation with schema validation.

**Note:** This follows similar structure to Architecture Planner. I'll provide the outline; detailed implementation mirrors 2.2.

#### Task 2.3.1: Create IaC Generator Prompt

**File:** Create `backend/config/prompts/iac_generator_prompt.yaml`

**Key Features:**
- Bicep workflow: Schema lookup → Code generation
- Terraform workflow: Best practices → Code generation
- Azure naming compliance
- Modular structure (environments, modules, policies)

**Estimated Effort:** 1 day

---

#### Task 2.3.2: Implement IaC Generator Node

**File:** Create `backend/app/agents_system/langgraph/nodes/iac_generator.py`

**Workflow:**
1. Detect format (Bicep or Terraform)
2. Call format-specific tool (bicepschema or terraform best practices)
3. Generate code with validation
4. Return structured IaC files

**Estimated Effort:** 1-2 days

---

#### Task 2.3.3: Add Routing Logic for IaC Generator

**File:** `backend/app/agents_system/langgraph/nodes/stage_routing.py`

**Detection:**
- User mentions "generate Bicep", "create Terraform", "IaC code"
- Project stage is "iac"

**Estimated Effort:** 0.5 day

---

#### Task 2.3.4: Integrate Bicep Schema and Terraform Best Practices Tools

**MCP Tools:**
- `azure-mcp/bicepschema` - Lookup Bicep resource schemas
- `azure-mcp/azureterraformbestpractices` - Terraform recommendations

**Steps:**
1. [ ] Verify MCP tools are available in environment
2. [ ] Add tool bindings to IaC Generator agent
3. [ ] Test schema lookups
4. [ ] Test best practices retrieval

**Estimated Effort:** 1 day

---

#### Task 2.3.5: Test IaC Generator Integration

**Test Scenarios:**
- Request Bicep code for architecture
- Request Terraform code for architecture
- Validate generated code compiles (Bicep CLI, Terraform validate)

**Estimated Effort:** 2 days

---

### Task 2.4: Reduce Main Agent Prompt Complexity

**Objective:** Now that Architecture Planner and IaC Generator handle specialized tasks, remove those details from main prompt.

**File:** `backend/config/prompts/agent_prompts.yaml`

**Sections to Simplify:**

1. **Architecture Design Instructions**
   - Remove detailed diagram generation instructions
   - Add: "For architecture design requests, delegate to Architecture Planner sub-agent"

2. **IaC Instructions**
   - Remove Bicep/Terraform workflow details
   - Add: "For IaC generation requests, delegate to IaC Generator sub-agent"

3. **NFR Analysis**
   - Remove detailed NFR analysis instructions (now in Architecture Planner)
   - Keep: High-level mention of NFR importance

**Expected Result:**
- Main prompt reduced from ~300 lines to ~220-250 lines
- Clearer responsibilities: Conversation, clarification, ADR creation, validation
- Specialized tasks delegated to sub-agents

**Steps:**
1. [ ] Identify sections that duplicate sub-agent prompts
2. [ ] Replace with delegation instructions
3. [ ] Test that main agent still handles non-specialized tasks well
4. [ ] Verify E2E tests still pass

**Estimated Effort:** 1 day

---

### Task 2.5: Document Phase 2 Changes

**Files to Create/Update:**

1. **docs/MULTI_AGENT_ARCHITECTURE.md** (already created in 2.1)
   - [ ] Add implementation details
   - [ ] Add LangGraph diagram (actual graph structure)
   - [ ] Document routing logic

2. **backend/config/prompts/README.md**
   - [ ] Document new prompt files (architecture_planner, iac_generator)
   - [ ] Explain when each agent is invoked
   - [ ] Update version to 2.0

3. **docs/SYSTEM_ARCHITECTURE.md**
   - [ ] Update "Agent System" section with multi-agent approach
   - [ ] Add sub-agent descriptions

4. **CHANGELOG.md**
   ```markdown
   ## [2.0.0] - 2026-02-XX

   ### Added
   - **Multi-Agent Architecture:** Decomposed monolithic agent into specialized sub-agents
   - **Architecture Planner Agent:** Specialized in target architecture design, NFR analysis, diagram generation
   - **IaC Generator Agent:** Specialized in Bicep/Terraform code generation with schema validation
   - **Conditional Routing:** LangGraph routes to appropriate agent based on request type

   ### Changed
   - **Main Agent Simplified:** Reduced prompt complexity by moving specialized tasks to sub-agents
   - **Prompt Size:** Main agent prompt reduced from 357 → ~240 lines

   ### Improved
   - Higher quality architecture proposals with dedicated agent
   - Production-ready IaC code with schema validation
   - Clearer agent responsibilities and better maintainability
   ```

**Estimated Effort:** 1 day

---

### Phase 2 Summary

**Total Effort:** 2-3 weeks

**Deliverables:**
- ✅ Architecture Planner sub-agent (design, NFR analysis, diagrams)
- ✅ IaC Generator sub-agent (Bicep/Terraform with validation)
- ✅ Conditional routing in LangGraph
- ✅ Main agent prompt simplified (240 lines)
- ✅ All tests passing
- ✅ Documentation updated

**Next Phase Readiness:**
- [ ] Phase 2 fully tested and validated
- [ ] User feedback on architecture quality
- [ ] Performance metrics collected (latency, token usage)

---

## Phase 3: Optional Specialized Agents (SaaS Advisor + Cost Estimator)

**Duration:** 2 weeks  
**Goal:** Add optional specialized capabilities for SaaS scenarios and cost estimation

### Prerequisites
- [x] Phase 2 complete and validated
- [ ] Create feature branch: `feature/optional-agents`
- [ ] Confirm SaaS scenarios and cost estimation are needed

---

### Task 3.1: Implement SaaS Advisor Sub-Agent (Optional Activation Only)

**Objective:** Add SaaS-specific guidance ONLY when explicitly in scope.

#### Task 3.1.1: Create SaaS Advisor Prompt

**File:** Create `backend/config/prompts/saas_advisor_prompt.yaml`

**Key Features:**
- B2B vs B2C distinction
- Tenant isolation patterns (shared/siloed/pooled)
- Noisy neighbor mitigation
- Deployment stamps pattern
- **IMPORTANT:** Clear scope - only activate for SaaS scenarios

**Estimated Effort:** 1 day

---

#### Task 3.1.2: Implement SaaS Advisor Node with Strict Triggers

**File:** Create `backend/app/agents_system/langgraph/nodes/saas_advisor.py`

**Trigger Conditions (Strict):**
```python
def _should_route_to_saas_advisor(state: AAAGraphState) -> bool:
    """
    ONLY route to SaaS Advisor when SaaS explicitly in scope.
    
    Do NOT activate for:
    - Regular web applications
    - Single-tenant enterprise apps
    - Internal tools
    """
    last_message = state["messages"][-1].content.lower()
    
    # Explicit SaaS keywords
    saas_keywords = [
        "saas", "multi-tenant", "multitenant", "b2b saas", "b2c saas",
        "tenant isolation", "subscription-based", "saas architecture"
    ]
    
    explicit_saas = any(keyword in last_message for keyword in saas_keywords)
    
    # User explicitly asks about SaaS suitability
    asking_about_saas = any(phrase in last_message for phrase in [
        "should this be saas", "is saas appropriate", "saas or not"
    ])
    
    return explicit_saas or asking_about_saas
```

**Estimated Effort:** 1 day

---

#### Task 3.1.3: Add SaaS Advisor Routing

**File:** `backend/app/agents_system/langgraph/nodes/stage_routing.py`

Add to routing logic with LOW priority (check after main tasks).

**Estimated Effort:** 0.5 day

---

#### Task 3.1.4: Test SaaS Advisor

**Test Scenarios:**
- ✅ Explicit SaaS request → SaaS Advisor activated
- ✅ Regular web app request → SaaS Advisor NOT activated
- ✅ Enterprise single-tenant → SaaS Advisor NOT activated
- ✅ User asks "should this be SaaS?" → SaaS Advisor provides analysis

**Estimated Effort:** 1 day

---

### Task 3.2: Implement Cost Estimator Sub-Agent

**Objective:** Integrate Azure Pricing API for TCO calculations.

#### Task 3.2.1: Research Azure Pricing API

**Steps:**
1. [ ] Review Azure Retail Prices API: https://learn.microsoft.com/rest/api/cost-management/retail-prices/azure-retail-prices
2. [ ] Identify required parameters for cost estimation
3. [ ] Design cost calculation logic

**Estimated Effort:** 0.5 day

---

#### Task 3.2.2: Create Cost Estimator Prompt

**File:** Create `backend/config/prompts/cost_estimator_prompt.yaml`

**Responsibilities:**
- Parse architecture proposal
- Extract Azure services and configurations
- Query Azure Pricing API
- Calculate monthly/annual costs
- Provide cost optimization recommendations
- Output pricing lines for `aaa_record_iac_and_cost`

**Estimated Effort:** 1 day

---

#### Task 3.2.3: Implement Azure Pricing Integration

**File:** `backend/app/services/pricing/retail_prices_client.py` (may already exist)

**API Integration:**
- Query: https://prices.azure.com/api/retail/prices
- Filter by: region, service, SKU
- Parse response and calculate costs

**Estimated Effort:** 1-2 days

---

#### Task 3.2.4: Implement Cost Estimator Node

**File:** Create `backend/app/agents_system/langgraph/nodes/cost_estimator.py`

**Workflow:**
1. Receive architecture proposal from state
2. Extract services (App Service, SQL Database, Storage, etc.)
3. Query pricing API for each service
4. Calculate total monthly cost
5. Suggest optimizations (reserved instances, right-sizing)
6. Return pricing lines

**Estimated Effort:** 2 days

---

#### Task 3.2.5: Add Cost Estimator Routing

**Trigger:** User asks "how much will this cost" or "cost estimation"

**Estimated Effort:** 0.5 day

---

#### Task 3.2.6: Test Cost Estimator

**Test Scenarios:**
- Architecture with 5 services → Accurate cost estimate
- Compare with Azure Pricing Calculator manually
- Test cost optimization recommendations

**Estimated Effort:** 1 day

---

### Task 3.3: Final Testing & Documentation

**Full System Testing:**
- [ ] Test all agent routing paths
- [ ] Verify no unintended agent activations
- [ ] Performance testing (latency, token usage per agent)
- [ ] Load testing (concurrent requests)

**Documentation:**
- [ ] Update all architecture docs
- [ ] Create user guide: "When Each Agent Activates"
- [ ] Update API documentation
- [ ] Create troubleshooting guide

**Estimated Effort:** 2-3 days

---

### Phase 3 Summary

**Total Effort:** 2 weeks

**Deliverables:**
- ✅ SaaS Advisor sub-agent (optional activation only)
- ✅ Cost Estimator sub-agent (pricing integration)
- ✅ Complete multi-agent system
- ✅ All tests passing
- ✅ Full documentation

---

## Post-Implementation: Monitoring & Iteration

### Task 4.1: Implement Agent Performance Monitoring

**Metrics to Track:**
- Agent routing decisions (which agent, how often)
- Token usage per agent
- Latency per agent
- User satisfaction (if feedback mechanism exists)
- Advisory quality scores (E2E tests)

**Tools:**
- Application Insights (if using Azure)
- Custom logging in orchestrator
- Dashboard for agent metrics

**Estimated Effort:** 1 week

---

### Task 4.2: User Feedback Collection

**Mechanism:**
- Add feedback buttons in UI: "Was this helpful?"
- Track which agent generated the response
- Analyze patterns: Which agent needs improvement?

**Estimated Effort:** 3-5 days (if UI changes needed)

---

### Task 4.3: Iterative Prompt Tuning

**Process:**
1. Collect 2 weeks of usage data
2. Identify poor-quality responses
3. Analyze which agent/prompt needs tuning
4. Update specific agent prompt
5. Test and deploy
6. Repeat

**Ongoing:** Continuous improvement cycle

---

## Success Metrics

### Phase 1 Success Criteria
- [ ] Main prompt reduced to ~300 lines
- [ ] Advisory quality scores maintain ≥4/8 (no regression)
- [ ] Agent asks clarifying questions when needed
- [ ] Target architecture always provided first
- [ ] Diagrams include NFR analysis

### Phase 2 Success Criteria
- [ ] Main prompt reduced to ~240 lines
- [ ] Architecture proposals include complete target design
- [ ] Diagrams are high-quality with NFR analysis
- [ ] IaC code is syntactically valid (Bicep/Terraform)
- [ ] Routing logic works correctly (95%+ accuracy)

### Phase 3 Success Criteria
- [ ] SaaS Advisor only activates when appropriate
- [ ] Cost estimates accurate (within 10% of manual calculation)
- [ ] All agents working harmoniously
- [ ] User feedback positive (>80% helpful)

---

## Risk Management

### Risk 1: Phase 1 Changes Break Existing Behavior
**Mitigation:**
- Run full E2E test suite before and after each change
- Keep backup of original prompt
- Gradual rollout with A/B testing if possible

### Risk 2: LangGraph Routing Errors
**Mitigation:**
- Extensive unit tests for routing logic
- Logging for all routing decisions
- Fallback to main agent on errors

### Risk 3: Sub-Agent Hallucination or Quality Issues
**Mitigation:**
- Few-shot examples in each sub-agent prompt
- Validation layer before returning to user
- Monitor advisory quality scores per agent

### Risk 4: Increased Latency with Multiple Agents
**Mitigation:**
- Profile each agent's performance
- Optimize prompts for efficiency
- Consider caching for repeated patterns
- Use parallel execution where possible

### Risk 5: Token Cost Increase
**Mitigation:**
- Monitor token usage per agent
- Use cheaper models (gpt-4o-mini) for simpler agents
- Optimize prompts to reduce verbosity
- Set token limits per agent

---

## Appendix A: Testing Checklist

### Regression Tests (Run After Every Phase)
- [ ] scenario-a passes
- [ ] scenario-behavior passes
- [ ] Advisory quality ≥4/8
- [ ] All unit tests pass
- [ ] No new errors in logs

### New Feature Tests (Phase-Specific)

**Phase 1:**
- [ ] MCP-first behavior validated
- [ ] Clarification questions asked when needed
- [ ] Target architecture provided first
- [ ] Diagrams include NFR analysis

**Phase 2:**
- [ ] Architecture requests route to planner
- [ ] IaC requests route to generator
- [ ] Fallback to main agent works
- [ ] Generated IaC code compiles

**Phase 3:**
- [ ] SaaS Advisor only for SaaS scenarios
- [ ] Cost Estimator provides accurate estimates
- [ ] All routing paths tested

---

## Appendix B: Rollback Plan

If any phase introduces critical issues:

1. **Immediate Rollback**
   ```bash
   git revert <commit-hash>
   git push origin main
   ```

2. **Deploy Previous Version**
   - Use backup prompt: `agent_prompts.yaml.backup-YYYY-MM-DD`
   - Restart services

3. **Root Cause Analysis**
   - Review logs for errors
   - Identify which change caused issue
   - Create hotfix branch

4. **Gradual Re-introduction**
   - Fix issue in isolation
   - Test thoroughly
   - Deploy with monitoring

---

## Appendix C: Communication Plan

### Stakeholder Updates

**Weekly Status Updates:**
- Phase completion status
- Metrics: prompt size, test pass rate, quality scores
- Blockers and risks
- Next week's plan

**Demo Sessions:**
- End of Phase 1: Show improved agent behavior
- End of Phase 2: Demonstrate multi-agent routing
- End of Phase 3: Complete system walkthrough

**Documentation:**
- Keep README.md updated
- Update API docs for any endpoint changes
- Maintain CHANGELOG.md

---

## Conclusion

This implementation plan provides a structured, incremental approach to transforming AAA from a single-agent system to a sophisticated multi-agent architecture. By following this plan, we will:

✅ Reduce main agent complexity  
✅ Improve architecture quality through specialization  
✅ Enable production-ready IaC generation  
✅ Maintain system stability through phased rollout  
✅ Achieve enterprise-grade Azure architecture assistant

**Total Timeline:** 5-6 weeks  
**Total Effort:** ~45-60 days of development work  
**Risk Level:** Medium (mitigated through phased approach and testing)

**Next Step:** Review this plan with the team, adjust timelines/priorities, and begin Phase 1 with prompt refactoring.
