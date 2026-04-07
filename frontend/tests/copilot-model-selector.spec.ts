import { expect, test } from "@playwright/test";

/**
 * Copilot model selector E2E tests.
 *
 * These tests verify that the model dropdown in the navigation bar
 * correctly reflects the Copilot SDK model list when the Copilot
 * provider is active.  API responses are intercepted so the tests
 * run without a live backend.
 */

/** Minimal project list so the page loads cleanly. */
function mockProjectRoutes(page: import("@playwright/test").Page) {
  return Promise.all([
    page.route("**/api/projects", async (route) => {
      if (route.request().method() !== "GET") {
        await route.fallback();
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          projects: [{ id: "proj-1", name: "E2E Model Test" }],
        }),
      });
    }),
    page.route("**/api/projects/proj-1", async (route) => {
      if (route.request().method() !== "GET") {
        await route.fallback();
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          project: {
            id: "proj-1",
            name: "E2E Model Test",
            textRequirements: "",
            createdAt: "2026-03-27T00:00:00Z",
          },
        }),
      });
    }),
    page.route("**/api/projects/proj-1/state", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          projectState: {
            projectId: "proj-1",
            context: { summary: "", objectives: [], targetUsers: "", scenarioType: "" },
            technicalConstraints: { constraints: [], assumptions: [] },
            openQuestions: [],
            lastUpdated: "2026-03-27T00:00:00Z",
            requirements: [],
            assumptions: [],
            clarificationQuestions: [],
            candidateArchitectures: [],
            adrs: [],
            findings: [],
            diagrams: [],
            iacArtifacts: [],
            costEstimates: [],
            traceabilityLinks: [],
            mindMapCoverage: {},
            traceabilityIssues: [],
            mindMap: {},
            referenceDocuments: [],
            mcpQueries: [],
            iterationEvents: [],
          },
        }),
      });
    }),
    page.route("**/api/projects/proj-1/messages**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ messages: [] }),
      });
    }),
  ]);
}

/** Build the /settings/llm-options response with Copilot provider models. */
function buildLLMOptions(
  copilotModels: { id: string; name: string }[],
  activeModel = "gpt-5.2",
) {
  return {
    activeProvider: "copilot",
    activeModel,
    providers: [
      {
        id: "copilot",
        name: "GitHub Copilot",
        status: "available",
        statusMessage: null,
        selected: true,
        models: copilotModels.map((m) => ({
          id: m.id,
          name: m.name,
          contextWindow: 128000,
          pricing: null,
        })),
        auth: {
          available: true,
          authenticated: true,
          state: "active",
          login: "testuser",
          authType: "pat",
          host: null,
          statusMessage: null,
          cliPath: null,
          quota: null,
        },
      },
    ],
  };
}

/**
 * Helper: mock the settings/llm-options endpoint with given models.
 * Supports both initial load (refresh=false) and explicit refresh (refresh=true).
 */
function mockLLMOptions(
  page: import("@playwright/test").Page,
  copilotModels: { id: string; name: string }[],
  activeModel = "gpt-5.2",
) {
  return page.route("**/api/settings/llm-options**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(buildLLMOptions(copilotModels, activeModel)),
    });
  });
}

// ── Tests ────────────────────────────────────────────────────────────

test.describe("Copilot model selector", () => {
  test("displays all SDK models in the model dropdown", async ({
    page,
  }) => {
    const sdkModels = [
      { id: "gpt-4.1", name: "GPT-4.1" },
      { id: "gpt-5-mini", name: "GPT-5 mini" },
      { id: "gpt-5.1", name: "GPT-5.1" },
      { id: "gpt-5.2", name: "GPT-5.2" },
      { id: "claude-sonnet-4.6", name: "Claude Sonnet 4.6" },
      { id: "claude-opus-4.6", name: "Claude Opus 4.6" },
      { id: "claude-haiku-4.5", name: "Claude Haiku 4.5" },
    ];

    await mockProjectRoutes(page);
    await mockLLMOptions(page, sdkModels, "gpt-5.2");

    await page.goto("/project/proj-1");

    const modelSelect = page.locator('select[aria-label="LLM Model"]');
    await expect(modelSelect).toBeVisible();

    // Verify all SDK models appear as options
    for (const model of sdkModels) {
      await expect(modelSelect.locator(`option[value="${model.id}"]`)).toBeAttached();
    }

    // Verify total option count: models + separator + refresh = models.length + 2
    const allOptions = modelSelect.locator("option");
    const count = await allOptions.count();
    expect(count).toBe(sdkModels.length + 2);
  });

  test("model dropdown reflects many subscription-scoped models for Copilot", async ({
    page,
  }) => {
    // SDK returns only subscription-scoped models — verify all are rendered.
    const manyModels = [
      { id: "claude-sonnet-4.6", name: "Claude Sonnet 4.6" },
      { id: "claude-sonnet-4.5", name: "Claude Sonnet 4.5" },
      { id: "claude-haiku-4.5", name: "Claude Haiku 4.5" },
      { id: "claude-opus-4.6", name: "Claude Opus 4.6" },
      { id: "claude-opus-4.6-fast", name: "Claude Opus 4.6 fast" },
      { id: "claude-opus-4.5", name: "Claude Opus 4.5" },
      { id: "claude-sonnet-4", name: "Claude Sonnet 4" },
      { id: "gpt-5.3-codex", name: "GPT-5.3 Codex" },
      { id: "gpt-5.2-codex", name: "GPT-5.2 Codex" },
      { id: "gpt-5.2", name: "GPT-5.2" },
      { id: "gpt-5.1-codex-max", name: "GPT-5.1 Codex Max" },
      { id: "gpt-5.1-codex", name: "GPT-5.1 Codex" },
      { id: "gpt-5.1", name: "GPT-5.1" },
      { id: "gpt-5.1-codex-mini", name: "GPT-5.1 Codex Mini" },
      { id: "gpt-5-mini", name: "GPT-5 mini" },
      { id: "gpt-4.1", name: "GPT-4.1" },
    ];

    await mockProjectRoutes(page);
    await mockLLMOptions(page, manyModels, "gpt-5.2");

    await page.goto("/project/proj-1");

    const modelSelect = page.locator('select[aria-label="LLM Model"]');
    await expect(modelSelect).toBeVisible();

    // Core assertion: all subscription models are present
    const modelOptions = modelSelect.locator("option:not([disabled])");
    const enabledCount = await modelOptions.count();
    // subtract 1 for the "Refresh models" option
    const modelCount = enabledCount - 1;
    expect(modelCount).toBe(manyModels.length);
  });

  test("selecting a model triggers the set-selection API", async ({
    page,
  }) => {
    const models = [
      { id: "gpt-5.2", name: "GPT-5.2" },
      { id: "gpt-5-mini", name: "GPT-5 mini" },
      { id: "claude-sonnet-4.6", name: "Claude Sonnet 4.6" },
    ];

    await mockProjectRoutes(page);
    await mockLLMOptions(page, models, "gpt-5.2");

    // Intercept the PUT to verify it happens
    let selectionPayload: { provider_id: string; model_id: string } | null = null;
    await page.route("**/api/settings/llm-selection", async (route) => {
      if (route.request().method() !== "PUT") {
        await route.fallback();
        return;
      }
      selectionPayload = JSON.parse(route.request().postData() ?? "{}");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          currentModel: "claude-sonnet-4.6",
          currentProvider: "copilot",
          message: "Provider changed to copilot / claude-sonnet-4.6",
        }),
      });
    });

    await page.goto("/project/proj-1");

    const modelSelect = page.locator('select[aria-label="LLM Model"]');
    await expect(modelSelect).toBeVisible();

    await modelSelect.selectOption("claude-sonnet-4.6");

    // Wait for the PUT request to complete
    await expect
      .poll(() => selectionPayload, { timeout: 5000 })
      .not.toBeNull();

    expect(selectionPayload).toEqual({
      provider_id: "copilot",
      model_id: "claude-sonnet-4.6",
    });
  });

  test("refresh option triggers a refreshed model list", async ({
    page,
  }) => {
    const initialModels = [
      { id: "gpt-5.2", name: "GPT-5.2" },
      { id: "gpt-5-mini", name: "GPT-5 mini" },
    ];
    const refreshedModels = [
      ...initialModels,
      { id: "claude-sonnet-4.6", name: "Claude Sonnet 4.6" },
      { id: "gpt-4.1", name: "GPT-4.1" },
    ];

    let callCount = 0;
    await mockProjectRoutes(page);

    await page.route("**/api/settings/llm-options**", async (route) => {
      callCount++;
      const url = route.request().url();
      const isRefresh = url.includes("refresh=true");
      const models = isRefresh ? refreshedModels : initialModels;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(buildLLMOptions(models, "gpt-5.2")),
      });
    });

    await page.goto("/project/proj-1");

    const modelSelect = page.locator('select[aria-label="LLM Model"]');
    await expect(modelSelect).toBeVisible();

    // Verify initial model count
    const initialOptions = modelSelect.locator("option:not([disabled])");
    // Wait for initial load
    await expect(initialOptions).toHaveCount(initialModels.length + 1); // +1 for Refresh

    // Click the refresh option
    await modelSelect.selectOption("__refresh__");

    // After refresh, verify the expanded model list
    await expect(initialOptions).toHaveCount(refreshedModels.length + 1, {
      timeout: 5000,
    });
  });
});
