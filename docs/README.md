# Azure Architect Assistant - Documentation

This folder contains all project documentation organized by topic area.

## 📚 Table of Contents

### 🏗️ Architecture & System Design

- **[PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md)** - High-level project goals, features, and architecture
- **[SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md)** - Detailed system design and component interactions
- **[MULTI_AGENT_ARCHITECTURE.md](./MULTI_AGENT_ARCHITECTURE.md)** - Agent orchestration and workflow design

### 💻 Development Guides

- **[DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)** - Getting started with development
- **[BACKEND_REFERENCE.md](./BACKEND_REFERENCE.md)** - Backend code structure, patterns, and conventions
- **[FRONTEND_REFERENCE.md](./FRONTEND_REFERENCE.md)** - Frontend architecture and component guide

### 🎨 User Experience

- **[UX_IDE_WORKFLOW.md](./UX_IDE_WORKFLOW.md)** - IDE-like workspace interface and workflows
- **[UNIFIED_UX_IMPLEMENTATION_CHECKLIST.md](./UNIFIED_UX_IMPLEMENTATION_CHECKLIST.md)** - UX implementation status

### 🚀 Implementation Plans & Specs

#### Active Implementation
- **[waf_normalization_implementation/](./waf_normalization_implementation/)** - 📋 **WAF Checklist Normalization to Database**
  - Complete task-by-task implementation plan
  - Progress tracking checklist
  - Testing and deployment procedures
  - [Start here →](./waf_normalization_implementation/README.md)

#### Completed Implementations
- **[LANGGRAPH_MIGRATION_COMPLETE.md](./LANGGRAPH_MIGRATION_COMPLETE.md)** - LangGraph migration completion report
- **[P0_IMPLEMENTATION_COMPLETE.md](./P0_IMPLEMENTATION_COMPLETE.md)** - Phase 0 completion summary
- **[P1_IMPLEMENTATION_COMPLETE.md](./P1_IMPLEMENTATION_COMPLETE.md)** - Phase 1 completion summary
- **[FRONTEND_REDESIGN_COMPLETE.md](./FRONTEND_REDESIGN_COMPLETE.md)** - Frontend redesign completion

#### Plans & Specs
- **[plan-normalizeWafChecklistToDb.prompt.prompt.md](./plan-normalizeWafChecklistToDb.prompt.prompt.md)** - Original WAF normalization plan (see implementation folder above for detailed tasks)
- **[LANGGRAPH_MIGRATION_PLAN.md](./LANGGRAPH_MIGRATION_PLAN.md)** - LangGraph migration strategy
- **[FRONTEND_REDESIGN_PLAN.md](./FRONTEND_REDESIGN_PLAN.md)** - Frontend redesign specifications
- **[HEADER_PROJECT_SELECTOR_PLAN.md](./HEADER_PROJECT_SELECTOR_PLAN.md)** - Project selector component spec
- **[IDE_WORKSPACE_TABS_SPEC.md](./IDE_WORKSPACE_TABS_SPEC.md)** - Workspace tabs specification
- **[PERFORMANCE_REMEDIATION_PLAN.md](./PERFORMANCE_REMEDIATION_PLAN.md)** - Performance optimization plan

### 🔍 Analysis & Research

- **[PHASE1_PROMPT_ANALYSIS.md](./PHASE1_PROMPT_ANALYSIS.md)** - Phase 1 prompt analysis
- **[PHASE1_COMPLETION_SUMMARY.md](./PHASE1_COMPLETION_SUMMARY.md)** - Phase 1 summary
- **[PHASE3_OPTIONAL_AGENTS.md](./PHASE3_OPTIONAL_AGENTS.md)** - Phase 3 optional agent specifications
- **[INDEXER_PERFORMANCE_ANALYSIS.json](./INDEXER_PERFORMANCE_ANALYSIS.json)** - Performance analysis data
- **[arch_mindmap.json](./arch_mindmap.json)** - Architecture mindmap data

### 📁 Subdirectories

- **[Agent_Enhancement/](./Agent_Enhancement/)** - Agent enhancement documentation
- **[refactor/](./refactor/)** - Refactoring plans and notes
- **[refs/](./refs/)** - Reference materials and external docs

---

## 🎯 Quick Navigation

### For New Contributors
1. Start with [PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md) to understand the project
2. Read [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) to set up your environment
3. Review [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md) for architectural context

### For Backend Development
1. [BACKEND_REFERENCE.md](./BACKEND_REFERENCE.md) - Code structure and patterns
2. [MULTI_AGENT_ARCHITECTURE.md](./MULTI_AGENT_ARCHITECTURE.md) - Agent system design

### For Frontend Development
1. [FRONTEND_REFERENCE.md](./FRONTEND_REFERENCE.md) - Component architecture
2. [UX_IDE_WORKFLOW.md](./UX_IDE_WORKFLOW.md) - User workflows and interactions

### For Current Implementation Work
**[WAF Normalization Implementation →](./waf_normalization_implementation/README.md)**

---

## 📋 Documentation Standards

All documentation in this folder follows these standards:

### Document Structure
- **Front matter**: Include "Last Updated" date and status
- **Table of Contents**: For documents > 100 lines
- **Clear sections**: Use hierarchical headers (h2, h3, h4)
- **Code examples**: Use syntax highlighting with language tags

### Naming Conventions
- **Plans**: `<TOPIC>_PLAN.md` (e.g., `MIGRATION_PLAN.md`)
- **Completions**: `<TOPIC>_COMPLETE.md` (e.g., `MIGRATION_COMPLETE.md`)
- **References**: `<TOPIC>_REFERENCE.md` (e.g., `API_REFERENCE.md`)
- **Specs**: `<TOPIC>_SPEC.md` (e.g., `COMPONENT_SPEC.md`)
- **Guides**: `<TOPIC>_GUIDE.md` (e.g., `DEVELOPMENT_GUIDE.md`)

### Link Conventions
- Use relative paths for internal documentation
- Always include descriptive link text
- Verify links after moving or renaming files

### Maintenance
- Update "Last Updated" metadata when making significant changes
- Keep implementation folders for active work (see `waf_normalization_implementation/`)
- Archive completed implementation plans with completion summaries

---

## 🔄 Document Lifecycle

1. **Planning Phase**: Create `<TOPIC>_PLAN.md` with detailed specifications
2. **Implementation Phase**: Create implementation folder with detailed task breakdown (see `waf_normalization_implementation/`)
3. **Completion Phase**: Create `<TOPIC>_COMPLETE.md` summarizing outcomes
4. **Maintenance Phase**: Update reference docs and guides as needed

---

## 📝 Contributing to Documentation

### When to Update Documentation

**You MUST update documentation when**:
- Adding new features or APIs
- Changing existing behavior
- Modifying architecture or design patterns
- Completing implementation phases
- Discovering issues or gotchas

**Update the appropriate document**:
- API changes → Reference docs (BACKEND_REFERENCE.md, FRONTEND_REFERENCE.md)
- Architecture changes → SYSTEM_ARCHITECTURE.md, MULTI_AGENT_ARCHITECTURE.md
- UX changes → UX_IDE_WORKFLOW.md
- Implementation progress → Update progress trackers in implementation folders
- New patterns → Add to reference guides

### How to Update Documentation

1. **Find the right document** (see navigation above)
2. **Make your changes** with clear, concise language
3. **Update "Last Updated"** metadata
4. **Verify links** still work
5. **Include in your PR** (documentation updates go with code changes)

### Creating New Documentation

If you need to create new documentation:

1. **Check if it fits** in an existing document first
2. **Use the naming conventions** from standards above
3. **Include front matter**: Last Updated, Status, Purpose
4. **Add to this README** in the appropriate section
5. **Link from related documents**

---

## 🆘 Getting Help

- **Architecture questions**: See SYSTEM_ARCHITECTURE.md
- **Development setup**: See DEVELOPMENT_GUIDE.md
- **Implementation details**: Check implementation folders (e.g., waf_normalization_implementation/)
- **Code patterns**: See BACKEND_REFERENCE.md or FRONTEND_REFERENCE.md

---

**Last Updated**: February 4, 2026  
**Maintained By**: Development Team
