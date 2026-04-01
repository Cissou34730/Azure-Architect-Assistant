# Frontend Documentation

Comprehensive human-facing frontend documentation.

## Contents

- [`FRONTEND_REFERENCE.md`](./FRONTEND_REFERENCE.md)
- [`UX_IDE_WORKFLOW.md`](./UX_IDE_WORKFLOW.md)
- [`UNIFIED_UX_IMPLEMENTATION_CHECKLIST.md`](./UNIFIED_UX_IMPLEMENTATION_CHECKLIST.md)

## Testing Notes

- The Azure model selector is covered by `frontend/tests/azure-model-selector.spec.ts` using mocked `/api/settings/llm-options` responses.
- Live Azure verification is covered by `frontend/tests/azure-e2e-chat.spec.ts`, which checks that GPT-5.x and Codex models appear in the selector and that the `Accor 3` project can send `Give me the NFR based on the inputs` through the real chat UI using the `aaadp` Azure deployment.

---

**Status**: Active  
**Last Updated**: 2026-04-01  
**Owner**: Engineering
