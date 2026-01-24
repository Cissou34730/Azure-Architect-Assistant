# Changelog

All notable changes to the Azure Architect Assistant project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
