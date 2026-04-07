import { ESLint } from "eslint";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { beforeAll, describe, expect, it } from "vitest";

function repoRoot(): string {
  return resolve(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
}

async function lintText(source: string, filePath: string) {
  const eslint = sharedEslint;
  const [result] = await eslint.lintText(source, {
    filePath: resolve(repoRoot(), filePath),
  });
  return result;
}

let sharedEslint: ESLint;

beforeAll(() => {
  sharedEslint = new ESLint({ cwd: repoRoot() });
}, 60_000);

describe("frontend architecture import boundaries", () => {
  it(
    "flags top-level shared modules that import features",
    async () => {
    const result = await lintText(
      'import "../../features/projects/pages/ProjectsPage";\nexport const sentinel = 1;\n',
      "frontend/src/shared/hooks/useToast.ts",
    );

    expect(result.messages).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          ruleId: "no-restricted-imports",
          severity: 2,
          message: expect.stringContaining(
            "Top-level shared frontend modules must not import from features.",
          ),
        }),
      ]),
    );
    },
    240_000,
  );

  it(
    "errors when feature modules reach into root service and hook compatibility shims",
    async () => {
    const result = await lintText(
      'import { startIngestion } from "../../../services/ingestionApi";\nexport const api = startIngestion;\n',
      "frontend/src/features/ingestion/components/IngestionWorkspace.tsx",
    );

    expect(result.messages).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          ruleId: "no-restricted-imports",
          severity: 2,
          message: expect.stringContaining(
            "Feature modules must not import root compatibility shims.",
          ),
        }),
      ]),
    );
    },
    60_000,
  );

  it(
    "errors when feature modules import remaining root type compatibility shims",
    async () => {
      const result = await lintText(
        'import type { ProjectState } from "../../../types/agent";\nexport type LoadedState = ProjectState;\n',
        "frontend/src/features/agent/components/ProjectStatePanel.tsx",
      );

      expect(result.messages).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            ruleId: "no-restricted-imports",
            severity: 2,
            message: expect.stringContaining(
              "Feature modules must not import root compatibility shims.",
            ),
          }),
        ]),
      );
    },
    60_000,
  );

  it(
    "errors when feature modules import the removed root api compatibility shim",
    async () => {
      const result = await lintText(
        'import type { ProjectState } from "../../../types/api";\nexport type LoadedState = ProjectState;\n',
        "frontend/src/features/projects/hooks/useProjectState.ts",
      );

      expect(result.messages).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            ruleId: "no-restricted-imports",
            severity: 2,
            message: expect.stringContaining(
              "Feature modules must not import the removed root api compatibility shim.",
            ),
          }),
        ]),
      );
    },
    60_000,
  );
});