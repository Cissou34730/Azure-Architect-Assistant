# Changelog

All notable changes to the Azure Architect Assistant project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
