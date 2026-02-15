# Changelog

All notable changes to the Azure Architect Assistant project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Mindmap-Guided Advisory Conversation Flow (non-blocking)**
  - Introduced explicit `mindmap_guidance` payload in LangGraph state for top-level architecture gap coaching.
  - Added dedicated advanced-graph step to carry mindmap guidance before agent execution.
  - Added stage-aware directive precedence policy:
    - Discovery-focused stages (`clarify`, `propose_candidate`) foreground mindmap coaching.
    - Validation stage keeps checklist execution priority and mindmap prompts advisory.

- **Follow-up Smoothness + Guardrails**
  - Added uncovered-topic prompt budget and dedup logic to reduce repetitive follow-up messages.
  - Added validation-stage WAF follow-up guardrail when checklist updates are missing and open items remain.

- **Tests for Guidance Policy and Persistence Safeguards**
  - Added focused tests for stage precedence, non-blocking guidance behavior, prompt dedup/budget logic, and validation-stage WAF follow-up safeguards.

### Changed

- **Top-level mindmap coverage scoring refinement**
  - Coverage now includes confidence values and weighted maturity heuristics (WAF status + findings evidence) to reduce noisy uncovered-topic prompts.

### Documentation

- Added implementation handoff document:
  - `docs/refactor/mindmap-guidance-waf-implementation-handoff.md`

## [1.3.0] - 2026-01-24

### Added - Optional Specialized Agents (Phase 3)

- **SaaS Advisor Sub-Agent** - Specialized agent for multi-tenant SaaS architecture guidance
  - Tenant Architecture Models: Silo (dedicated per tenant), Pool (shared with logical isolation), Bridge (hybrid approach)
  - Tenant Isolation Strategies: data layer (schemas, databases, encryption), compute layer (containers, processes), network layer (VNets, NSGs), storage layer (accounts, containers)
  - B2B vs B2C Patterns: SSO integration, tenant onboarding, billing models, customization levels
  - Noisy Neighbor Mitigation: rate limiting, resource quotas, circuit breakers, burst protection
  - Deployment Stamps: geographic stamps, tier-based stamps, capacity planning
  - Cost Analysis: per-tenant economics, pricing models (per-user, per-feature, tiered)
  - Strict activation: only on explicit SaaS keywords (saas, multi-tenant, B2B/B2C, tenant isolation)
  - Suitability analysis: "should this be SaaS?" questions with trade-off guidance
  - Prompt: 393 lines with comprehensive SaaS architecture patterns
  - Node implementation: saas_advisor.py (230 lines) with tenant model extraction

- **Cost Estimator Sub-Agent** - Specialized agent for Azure cost estimation and optimization
  - Azure Retail Prices API Integration: https://prices.azure.com/api/retail/prices with OData filters
  - Cost Calculation Formulas: hourly → monthly (730h) → annual (×12) → 3-year TCO (×3)
  - Regional Pricing Differences: +15% West Europe, +30% Brazil South, documented per region
  - Cost Optimization Strategies:
    - Reserved Instances: 40-60% savings for predictable workloads (1-year, 3-year)
    - Right-Sizing: match SKU to actual usage patterns
    - Azure Hybrid Benefit (AHB): 30-55% savings for SQL/Windows with existing licenses
    - Spot Instances: 70-90% savings for fault-tolerant workloads
    - Auto-Scaling: 75% savings for dev/test environments
    - Storage Tiering: Hot → Cool → Archive based on access patterns
  - Service-Specific Pricing: App Service tiers, SQL Database DTU/vCore, Storage redundancy, Functions consumption/premium, Cosmos DB models
  - Detailed Output Template: cost summary table, breakdown by service, optimization opportunities with quantified savings
  - Strict activation: only on explicit cost keywords (cost, price, pricing, how much, TCO, budget estimate)
  - Requires finalized architecture (candidateArchitectures exists)
  - Prompt: 349 lines with API integration guide and optimization strategies
  - Node implementation: cost_estimator.py (279 lines) with regex-based cost extraction
  - Pricing Client: Existing retail_prices_client.py (205 lines) with async, retry logic, pagination - verified adequate

- **Enhanced Multi-Agent Routing System** - Extended routing with 4 specialized agents
  - Routing Priority: IaC Generator (highest) → Architecture Planner → SaaS Advisor → Cost Estimator → Main Agent (lowest)
  - SaaS Advisor Routing:
    - should_route_to_saas_advisor(): strict keyword matching (saas, multi-tenant, B2B/B2C, tenant isolation, deployment stamps, noisy neighbor)
    - prepare_saas_advisor_handoff(): extracts tenant requirements (customer type, expected tenants, isolation level, compliance)
    - _extract_tenant_requirements(): regex parsing for tenant count, isolation level detection, compliance keywords
    - LOW priority (after IaC and Architecture)
  - Cost Estimator Routing:
    - should_route_to_cost_estimator(): cost keywords + architecture validation
    - prepare_cost_estimator_handoff(): architecture, resource list, region detection, environment detection
    - _detect_region(): parse Azure region from message/requirements (default: eastus)
    - _detect_environment(): production/dev/test (default: production)
    - LOWEST priority (after IaC, Architecture, SaaS)
  - Updated stage_routing.py: +211 lines for SaaS and Cost routing functions
  - Updated graph_factory.py: cost_estimator node, prepare_cost_handoff node, extended conditional routing

- **Comprehensive Testing Suite** - Validation for all agent routing scenarios
  - test_phase3_saas_advisor.py: 4 test scenarios
    - Explicit SaaS request (should activate)
    - Regular web app (should NOT activate)
    - Enterprise single-tenant (should NOT activate)
    - SaaS suitability question (should activate with analysis)
    - Result: 4/4 passing (100%)
  - test_phase3_cost_estimator.py: 4 test scenarios
    - 5-service architecture (cost range validation)
    - Optimization recommendations (RIs, right-sizing, AHB, spot)
    - Error handling (no architecture finalized)
    - Regional pricing differences (West Europe +15%)
    - Result: 4/4 passing (100%)
  - test_phase3_full_system.py: 8 test scenarios
    - All routing paths (IaC → Arch → SaaS → Cost → Main)
    - Priority verification for each agent
    - False positive checks (web app NOT SaaS, budget constraint NOT cost)
    - Performance testing (average latency: 0.0003s per routing decision)
    - Result: 8/8 passing (100%)
  - Total: 16 test scenarios, 100% passing rate

### Changed - Routing Logic Improvements

- **SaaS Advisor False Positive Fix**
  - Removed context_summary check to avoid false positives
  - Now only routes based on explicit keywords in user_message
  - Prevents "Design a web application for internal employee management" from triggering SaaS Advisor
  - Requires explicit SaaS intent from user

### Fixed - Import Path Corrections

- **Node Import Fixes**
  - Fixed import path in architecture_planner.py: aaa_candidate_tool instead of create_tools
  - Fixed import path in iac_generator.py: aaa_candidate_tool instead of create_tools
  - Fixed import path in saas_advisor.py: aaa_candidate_tool instead of create_tools
  - Fixed import path in cost_estimator.py: aaa_candidate_tool instead of create_tools
  - Resolved ModuleNotFoundError during test execution

### Documentation

- **Phase 3 Planning**
  - docs/PHASE3_OPTIONAL_AGENTS.md (458 lines): comprehensive implementation plan
  - SaaS Advisor specifications: tenant models, isolation strategies, B2B/B2C patterns
  - Cost Estimator specifications: API integration, TCO calculations, optimization strategies
  - Success criteria: strict activation, no false positives, 100% test coverage

- **Agent Activation Guide**
  - docs/AGENT_ACTIVATION_GUIDE.md: user-facing guide explaining when each agent activates
  - Routing priority explanation with examples
  - Keyword reference for each agent
  - Best practices for triggering specific agents

### Commits (Phase 3)

- fb276cd: Phase 3 setup and planning document
- 12af440: SaaS Advisor prompt creation
- cc2ce88: SaaS Advisor node implementation
- c04ce3e: SaaS Advisor routing logic
- 9cfe4e7: SaaS Advisor graph integration
- 606bdc4: Azure Pricing API research and Cost Estimator prompt
- e0b8d07: Cost Estimator node implementation
- ba062a1: Cost Estimator routing integration
- 80bad75: Comprehensive test scripts creation
- 5fd08a0, 7f7ee9f: Import path fixes
- 2897810: Test script refactoring (direct function calls)
- 5f5fe79, f3a392c, fffe0e9: False positive fixes and test updates

## [1.2.0] - 2026-01-24

### Added - Multi-Agent Architecture (Phase 2)

- **Architecture Planner Sub-Agent** - Specialized agent for complex architecture design
  - Handles complete target architecture design (production-ready)
  - Generates C4 model diagrams (System Context, Container) with Mermaid syntax
  - Creates functional flow diagrams (user journeys, business processes, integrations)
  - Comprehensive NFR analysis (Scalability, Performance, Security, Reliability, Maintainability, Trade-offs)
  - Phased delivery planning (optional MVP path when requested)
  - Automatic routing based on complexity indicators (multi-region, HA, DR, compliance, microservices)
  - Prompt: 160 lines with specialized architecture methodology
  - Node implementation: architecture_planner.py with graceful error fallback

- **IaC Generator Sub-Agent** - Specialized agent for Infrastructure as Code generation
  - Production-ready Bicep code generation with best practices
  - Production-ready Terraform code generation with best practices
  - Azure resource schema validation via MCP tools
  - Parameterization and modularization strategies
  - Resource dependency management
  - IaC linting and validation
  - Automatic routing when Bicep/Terraform requested and architecture finalized
  - Prompt: 175 lines with IaC best practices and schema validation
  - Node implementation: iac_generator.py with format detection

- **Multi-Agent Routing System** - Intelligent agent selection and handoff
  - Agent router node with conditional routing logic
  - should_route_to_architecture_planner(): keyword + complexity detection
  - should_route_to_iac_generator(): IaC keyword + architecture validation
  - Context handoff preparation with NFR extraction and resource list generation
  - State schema extensions: current_agent, agent_handoff_context, routing_decision, sub_agent_input/output
  - Updated graph_factory.py with conditional edges and multi-agent flow

### Changed - Main Agent Simplification

- **Simplified Main Agent Prompt** - Reduced from 351 to 293 lines (-16.5%, version 1.2)
  - Removed detailed C4 diagram generation rules (~40 lines) - delegated to Architecture Planner
  - Removed comprehensive NFR analysis methodology (~30 lines) - delegated to Architecture Planner
  - Removed IaC workflow details (~20 lines) - delegated to IaC Generator
  - Added Sub-Agent Delegation section with clear delegation criteria
  - Main agent now focuses on: requirement clarification, general guidance, orchestration
  - Simplified Core Methodology, Workload Classification, Requirement Clarification sections
  - Streamlined tools & persistence rules
  - Condensed few-shot examples
  - Updated Orchestration & Delivery Strategy with delegation decision points

### Documentation

- **MULTI_AGENT_ARCHITECTURE.md** - Comprehensive design document
  - Current LangGraph infrastructure analysis (14 files)
  - Target multi-agent architecture with routing design
  - Mermaid diagrams of current vs enhanced flows
  - State schema extensions and handoff context structure
  - Routing rules with code examples
  - Implementation strategy and rollout plan
  - Testing strategy and success criteria
  - Risk mitigation and future enhancements

### Technical Details

- **Files Added:**
  - backend/config/prompts/architecture_planner_prompt.yaml
  - backend/config/prompts/iac_generator_prompt.yaml
  - backend/app/agents_system/langgraph/nodes/architecture_planner.py
  - backend/app/agents_system/langgraph/nodes/iac_generator.py
  - docs/MULTI_AGENT_ARCHITECTURE.md

- **Files Modified:**
  - backend/config/prompts/agent_prompts.yaml (351→293 lines)
  - backend/app/agents_system/langgraph/state.py (+5 fields)
  - backend/app/agents_system/langgraph/graph_factory.py (+multi-agent routing)
  - backend/app/agents_system/langgraph/nodes/stage_routing.py (+routing logic)

- **Git Commits:**
  - e27b240: Architecture Planner implementation
  - 71bbe0d: IaC Generator implementation
  - 2f366be: Main agent prompt simplification

---

## [1.1.0] - 2026-01-24

### Enhanced

- **MCP-First Documentation Strategy** - Emphasize precise MCP queries over external web search
  - CONSTRUCT PRECISE QUERIES: Include service name + specific feature
  - Example: "Azure SQL Database Private Link configuration" NOT "SQL security"
  - NEVER suggest external web search engines or generic web queries
  - ALL recommendations MUST cite Microsoft Learn URLs

- **Ask Before Assuming Checklist** - Added critical requirements checklist for requirement gathering
  - 7 categories: Performance & Scale, Security & Compliance, Budget & Cost, Operations, Integration, Data, Users
  - Grouped asking strategy (max 5 per response)
  - Explain WHY information affects architecture decisions
  - Challenge risky user choices explicitly

- **Target Architecture Primary** - Always provide complete target architecture, MVP optional
  - PRIMARY OUTPUT: Always provide complete TARGET ARCHITECTURE first
  - Full production-ready design with all Azure services, sizing, multi-region setup, security, reliability
  - NFR Alignment Statement mandatory
  - Optional MVP only offered as question AFTER presenting target architecture
  - MVP defers complexity, does NOT remove requirements

- **C4 + Functional Flow Diagrams** - Require both technical and business perspective diagrams
  - C4 technical perspective: System Context (mandatory), Container (mandatory), Component (optional)
  - Functional flows: User Journey, Business Process, Cross-System Integration
  - **Mandatory NFR Analysis for every diagram** with 6 sections:
    - Purpose, Key Elements, Relationships
    - NFR Alignment: Scalability, Performance, Security, Reliability, Maintainability
    - Trade-offs, Assumptions
  - Complete NFR analysis example template provided

### Refactored

- **Agent Prompt Consolidation** - Reduced prompt complexity while preserving functionality
  - Consolidated tool instructions and persistence rules into single comprehensive section
  - Merged proactive behavior sections (2.A + 2.F)
  - Enhanced clarification rules, absorbed old 2.B into Section 4
  - Unified persistence rules in tool section
  - Simplified output structure with bullet lists
  - Streamlined guardrails, references Section 2
  - Trimmed few-shot examples to essential steps
  - Simplified stage-driven workflow
  - **Size reduction**: 378 lines → 351 lines (net -7% from original, -31% from refactoring before additions)

### Changed

- **Prompt Version**: Updated from 1.0 to 1.1
- **Section Numbering**: Sections renumbered after consolidation (removed duplicate Requirement Extraction)

### Fixed

- **E2E Test Runner**: Added missing logger import
- **Database Paths**: Corrected .env database paths (../../ → ../)

## [1.0.0] - 2026-01-12

### Initial Release

- Initial Azure Architect Assistant agent prompt
- ReAct workflow with LangGraph orchestration
- WAF-based analysis and C4 modeling
- Knowledge base integration (WAF, CAF)
- MCP client for Microsoft documentation
- AAA ProjectState persistence tools
