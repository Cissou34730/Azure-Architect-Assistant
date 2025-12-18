<!--
═══════════════════════════════════════════════════════════════════════════════
SYNC IMPACT REPORT - Constitution v1.0.0
═══════════════════════════════════════════════════════════════════════════════

VERSION CHANGE: 0.0.0 → 1.0.0
BUMP TYPE: MAJOR (Initial constitution establishment)

RATIONALE:
Initial creation of project constitution defining non-negotiable development
principles, automated deployment requirements, and governance framework for
Azure Architecture Assistant.

MODIFIED PRINCIPLES:
  ✓ III. Code Self-Documentation → Explicit Naming (NON-NEGOTIABLE)
     - Strengthened to mandate explicit names for all code elements
     - Added prohibition on abbreviations
     - Made NON-NEGOTIABLE
  ✓ IV. DRY → Zero Duplication (NON-NEGOTIABLE)
     - Strengthened from guideline to absolute requirement
     - Added "search before implement" mandate
     - Clarified logic vs. data distinction
     - Made NON-NEGOTIABLE

ADDED SECTIONS:
  ✓ Core Principles (I-V including automated deployment)
  ✓ Technology Stack (mandatory versions: TypeScript 5+, React 19+, TailwindCSS 4.1, Python 3.10+)
  ✓ Mandatory Instruction Files reference
  ✓ Development Workflow & Quality Gates
  ✓ Governance framework

TEMPLATES CONSISTENCY CHECK:
  ✅ .specify/templates/plan-template.md
     - Constitution Check section present (lines ~29-31)
     - Compatible with principle enforcement
     - No updates required
     
  ✅ .specify/templates/spec-template.md
     - User story structure supports principle validation
     - No updates required
     
  ✅ .specify/templates/tasks-template.md
     - Task organization aligns with quality gates
     - No updates required
     
  ✅ .github/prompts/*.md command files
     - No agent-specific references found
     - Generic guidance maintained
     - No updates required

DEFERRED ITEMS: None

FOLLOW-UP ACTIONS:
  □ Team review and acknowledgment of constitution
  □ Add constitution compliance check to CI/CD pipeline
  □ Update PR template to reference constitution
  □ Schedule first 6-month constitution review (June 2026)

═══════════════════════════════════════════════════════════════════════════════
-->

# Azure Architecture Assistant Constitution

## Core Principles

### I. Single Responsibility Principle (NON-NEGOTIABLE)
A function, class, or module MUST have one, and only one, reason to change.

- Keep components focused on a single purpose
- No mixing of unrelated responsibilities
- Violations require explicit justification in Constitution Check
- Code that cannot be clearly named has unclear responsibility

**Rationale**: SRP is the foundation of maintainability, testability, and debuggability. Multiple responsibilities multiply complexity exponentially.

### II. Automated Deployment (NON-NEGOTIABLE)
All features MUST be automatically deployable to production with zero human intervention.

- Feature branches deploy automatically when merged to main
- No manual steps in deployment pipeline
- Infrastructure changes are code (IaC)
- Rollback is automated
- Deployment configuration lives in repository
- Failed deployments block the pipeline

**Rationale**: Human intervention introduces errors, delays, and inconsistency. Automation ensures reliability, speed, and repeatability at scale.

### III. Explicit Naming (NON-NEGOTIABLE)
All modules, variables, functions, classes, and methods MUST have explicit, self-documenting names.

- Names describe intent completely: `days_until_expiration` not `d`, `calculate_monthly_revenue` not `calc`
- No abbreviations except universally recognized (HTTP, API, URL)
- Module/file names match their primary export/purpose
- Comments explain *why*, not *what*
- If code needs comments to explain what it does, the naming is insufficient

**Rationale**: Code is read 10x more than written. Explicit naming eliminates ambiguity, prevents bugs, and enables confident changes without documentation lookup.

### IV. Zero Duplication (NON-NEGOTIABLE)
There MUST be no duplicate logic anywhere in the codebase. Every piece of behavior exists exactly once.

- Copy-paste is prohibited — extract to shared utility/module/function
- Search codebase before implementing — if similar logic exists, reuse or refactor
- Duplicate code means fixing bugs in N places and N opportunities for divergence
- Prefer composition and pure functions for shared behavior
- Configuration/data can repeat; logic cannot
- Any new logic MUST reference the existing implementation evaluated and justify why reuse or extension was not possible


**Rationale**: Each duplication multiplies maintenance burden, bug density, and inconsistency risk. Single source of truth ensures reliability.

### V. YAGNI - You Aren't Gonna Need It
Build only what is required today. No speculative features.

- Implement current requirements, not imagined future ones
- Premature abstraction is premature optimization
- Simple first, refactor when proven necessary
- Feature flags over branches for incomplete work

**Rationale**: Unused code becomes unmaintained liability. Build for today with refactorability in mind.

### VI. Integration First (NON-NEGOTIABLE)
All new code MUST integrate with the existing codebase and reuse existing capabilities before introducing new ones.

- Existing code MUST be searched and evaluated before implementing new logic
- Reuse, extension, or adaptation is mandatory when equivalent behavior exists
- New code MUST be placed according to established architectural boundaries
- Creating parallel or competing implementations is prohibited
- When existing code is insufficient, extend via adapter/facade rather than duplication

**Rationale**: This project evolves within a large, existing professional codebase. Uncontrolled greenfield-style additions rapidly create fragmentation, duplication, and architectural decay.


## Technology Stack

**Mandatory Versions** (MUST NOT deviate without constitutional amendment):

**Frontend**:
- TypeScript 5+ (strict mode enabled)
- React 19+
- TailwindCSS 4.1 (exclusive styling solution — no other CSS frameworks)
- Vite (build tool)

**Backend**:
- Python 3.10+
- FastAPI (async framework)

**Constraints**:
- No mixing of styling approaches (TailwindCSS only)
- No introduction of new frameworks without explicit approval
- Dependency updates follow semantic versioning review process

**Rationale**: Standardized stack prevents fragmentation, reduces cognitive load, simplifies onboarding, and ensures consistent tooling across the codebase.

## Mandatory Instruction Files

**All code MUST comply with instruction files in `/.github/` directory.**

These files provide detailed implementation standards:

- **`.github/copilot-instructions.md`** → Project workflow, stack, structure
- **`.github/python-instruction.md`** → Python standards (applies to `**/*.py`)
- **`.github/copilot-typescript-instruction.md`** → TypeScript/React standards (applies to `**/*.ts`, `**/*.tsx`)

**Enforcement**: PRs failing instruction file compliance are blocked.

## Development Workflow

**Constitution Check (Mandatory)**: Every `plan.md` MUST include Constitution Check section before implementation:

```markdown
## Constitution Check
- [ ] I. Single Responsibility - PASS/FAIL/JUSTIFIED
- [ ] II. Automated Deployment - PASS/FAIL/JUSTIFIED  
- [ ] III. Explicit Naming - PASS/FAIL/JUSTIFIED
- [ ] IV. Zero Duplication - PASS/FAIL/JUSTIFIED
- [ ] V. YAGNI - PASS/FAIL/JUSTIFIED
- [ ] VI. Integration First - PASS/FAIL/JUSTIFIED
- [ ] VII. Existing code discovery performed and documented
- [ ] VII. Instruction files compliance verified

Violations: [If any FAIL/JUSTIFIED, explain rationale and mitigation]


Violations: [If any FAIL/JUSTIFIED, explain rationale and mitigation]
```

**Quality Gates (ALL MUST PASS)**:
- ✅ No SRP violations without justification
- ✅ Automated deployment path defined
- ✅ All names explicit (no abbreviations, no unclear variable/function/class/module names)
- ✅ Zero duplicate logic (codebase searched for existing implementations)
- ✅ Complies with applicable `.github/*.md` instruction files
- ✅ Critical paths tested
- ✅ No new frameworks without approval

**Feature Branch Flow**: `feature → PR → constitution check → tests pass → auto-merge → auto-deploy → production`

**Refactoring Obligations**:
- Refactoring MUST be planned explicitly in `tasks.md`
- Tasks may not be considered DONE if refactoring steps are skipped
- Each phase MUST include a Hardening step (structure, duplication, boundaries)
- Refactoring tasks MUST NOT introduce new features


Manual gates break Principle II.

## Governance

**Authority**: This constitution supersedes all other practices. Conflicts resolve in favor of constitution principles. Detailed implementation guidance lives in `.github/*.md` instruction files.

**Amendments**:
1. Document rationale and impact
2. Team review and approval
3. Update version per semantic versioning
4. Migrate affected code
5. Update sync impact report

**Versioning**: MAJOR.MINOR.PATCH
- **MAJOR**: Principle removal/redefinition, stack change
- **MINOR**: New principle, expanded guidance
- **PATCH**: Clarifications, typo fixes

**Review Cadence**: Constitution review every 6 months. Emergency review on major architectural change. First review: June 2026.

**Version**: 1.0.0 | **Ratified**: 2025-12-17 | **Last Amended**: 2025-12-17
