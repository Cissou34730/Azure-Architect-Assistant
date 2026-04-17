# Frontend Documentation

Comprehensive human-facing frontend documentation.

## Contents

- [`FRONTEND_REFERENCE.md`](./FRONTEND_REFERENCE.md)
- [`UX_IDE_WORKFLOW.md`](./UX_IDE_WORKFLOW.md)
- [`UNIFIED_UX_IMPLEMENTATION_CHECKLIST.md`](./UNIFIED_UX_IMPLEMENTATION_CHECKLIST.md)

## Testing Notes

- The Azure model selector is covered by `frontend/tests/azure-model-selector.spec.ts` using mocked `/api/settings/llm-options` responses.
- Live Azure verification is covered by `frontend/tests/azure-e2e-chat.spec.ts`, which checks that GPT-5.x and Codex models appear in the selector and that the `Accor 3` project can send `Give me the NFR based on the inputs` through the real chat UI using the `aaadp` Azure deployment.

## Current Frontend Status

- Projects workspace shell, navigation, and static tab content are now driven by manifest and registry modules under `frontend/src/features/projects/`.
- The unified project workspace now includes first-class notes, chat review, quality-gate, and trace tabs; the old standalone `AgentChatWorkspace` surface has been retired.
- The former root `frontend/src/{hooks,services,types}` compatibility layer has been removed.
- Feature modules now resolve agent, ingestion, knowledge, settings, proposal, and diagram imports directly from canonical `features/*` modules, with ESLint enforcing the boundary.

---

**Status**: Active  
**Last Updated**: 2026-04-17  
**Owner**: Engineering
