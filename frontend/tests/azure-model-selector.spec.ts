import { expect, test } from "@playwright/test";

/**
 * Azure OpenAI model selector E2E tests.
 *
 * Verifies that the model dropdown correctly displays all chat-capable
 * models returned by the Azure OpenAI /openai/models endpoint when the
 * Azure provider is active.  API responses are intercepted so the tests
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
          projects: [{ id: "proj-1", name: "Azure Model Test" }],
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
            name: "Azure Model Test",
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

/** Build /settings/llm-options response with an Azure provider and models. */
function buildAzureLLMOptions(
  azureModels: { id: string; name: string }[],
  activeModel: string,
) {
  return {
    activeProvider: "azure",
    activeModel,
    providers: [
      {
        id: "azure",
        name: "Azure OpenAI",
        status: "available",
        statusMessage: null,
        selected: true,
        models: azureModels.map((m) => ({
          id: m.id,
          name: m.name,
          contextWindow: 128000,
          pricing: null,
        })),
        auth: null,
      },
    ],
  };
}

/** Mock the settings/llm-options endpoint with Azure models. */
function mockAzureLLMOptions(
  page: import("@playwright/test").Page,
  azureModels: { id: string; name: string }[],
  activeModel: string,
) {
  return page.route("**/api/settings/llm-options**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(buildAzureLLMOptions(azureModels, activeModel)),
    });
  });
}

// ── Tests ────────────────────────────────────────────────────────────

test.describe("Azure OpenAI model selector", () => {
  test("displays all Azure chat-capable models in the dropdown", async ({
    page,
  }) => {
    // Simulate what the backend returns after calling /openai/models on Azure
    const azureModels = [
      { id: "gpt-35-turbo", name: "gpt-35-turbo" },
      { id: "gpt-4", name: "gpt-4" },
      { id: "gpt-4o", name: "gpt-4o" },
      { id: "gpt-4o-mini", name: "gpt-4o-mini" },
      { id: "o1-mini", name: "o1-mini" },
      { id: "o1-preview", name: "o1-preview" },
      { id: "o4-mini", name: "o4-mini" },
    ];

    await mockProjectRoutes(page);
    await mockAzureLLMOptions(page, azureModels, "gpt-4o-mini");

    await page.goto("/project/proj-1");

    const modelSelect = page.locator('select[aria-label="LLM Model"]');
    await expect(modelSelect).toBeVisible();

    // Verify all Azure models appear as options
    for (const model of azureModels) {
      await expect(
        modelSelect.locator(`option[value="${model.id}"]`),
      ).toBeAttached();
    }

    // Total options: models + separator + refresh = models.length + 2
    const allOptions = modelSelect.locator("option");
    const count = await allOptions.count();
    expect(count).toBe(azureModels.length + 2);
  });

  test("displays comprehensive model list including GPT-5.3, GPT-5.4, and Codex models", async ({
    page,
  }) => {
    // Full model catalog including latest GPT-5.x and Codex models
    const azureModels = [
      { id: "aaadp", name: "gpt-4o-mini (aaadp)" },
      { id: "gpt-35-turbo", name: "gpt-35-turbo" },
      { id: "gpt-4", name: "gpt-4" },
      { id: "gpt-4o", name: "gpt-4o" },
      { id: "gpt-4o-mini", name: "gpt-4o-mini" },
      { id: "gpt-4.1-2025-04-14", name: "gpt-4.1-2025-04-14" },
      { id: "gpt-4.1-mini-2025-04-14", name: "gpt-4.1-mini-2025-04-14" },
      { id: "gpt-4.1-nano-2025-04-14", name: "gpt-4.1-nano-2025-04-14" },
      { id: "gpt-5-2025-08-07", name: "gpt-5-2025-08-07" },
      { id: "gpt-5-mini-2025-08-07", name: "gpt-5-mini-2025-08-07" },
      { id: "gpt-5-codex-2025-09-15", name: "gpt-5-codex-2025-09-15" },
      { id: "gpt-5.1-2025-11-13", name: "gpt-5.1-2025-11-13" },
      { id: "gpt-5.1-codex-2025-11-13", name: "gpt-5.1-codex-2025-11-13" },
      { id: "gpt-5.1-codex-mini-2025-11-13", name: "gpt-5.1-codex-mini-2025-11-13" },
      { id: "gpt-5.1-codex-max-2025-12-04", name: "gpt-5.1-codex-max-2025-12-04" },
      { id: "gpt-5.2-chat-2025-12-11", name: "gpt-5.2-chat-2025-12-11" },
      { id: "gpt-5.3-codex-2026-02-20", name: "gpt-5.3-codex-2026-02-20" },
      { id: "gpt-5.3-chat-2026-03-03", name: "gpt-5.3-chat-2026-03-03" },
      { id: "gpt-5.4-nano-2026-03-17", name: "gpt-5.4-nano-2026-03-17" },
      { id: "gpt-5.4-mini-2026-03-17", name: "gpt-5.4-mini-2026-03-17" },
      { id: "codex-mini-2025-05-16", name: "codex-mini-2025-05-16" },
      { id: "o1-mini", name: "o1-mini" },
      { id: "o3-mini", name: "o3-mini" },
      { id: "o4-mini", name: "o4-mini" },
    ];

    await mockProjectRoutes(page);
    await mockAzureLLMOptions(page, azureModels, "aaadp");

    await page.goto("/project/proj-1");

    const modelSelect = page.locator('select[aria-label="LLM Model"]');
    await expect(modelSelect).toBeVisible();

    // Verify ALL models appear
    for (const model of azureModels) {
      await expect(
        modelSelect.locator(`option[value="${model.id}"]`),
        `Model ${model.id} should be in the dropdown`,
      ).toBeAttached();
    }

    // Specifically verify GPT-5.3 models
    await expect(modelSelect.locator('option[value="gpt-5.3-chat-2026-03-03"]')).toBeAttached();
    await expect(modelSelect.locator('option[value="gpt-5.3-codex-2026-02-20"]')).toBeAttached();

    // Specifically verify GPT-5.4 models
    await expect(modelSelect.locator('option[value="gpt-5.4-nano-2026-03-17"]')).toBeAttached();
    await expect(modelSelect.locator('option[value="gpt-5.4-mini-2026-03-17"]')).toBeAttached();

    // Specifically verify Codex models
    await expect(modelSelect.locator('option[value="codex-mini-2025-05-16"]')).toBeAttached();
    await expect(modelSelect.locator('option[value="gpt-5-codex-2025-09-15"]')).toBeAttached();
    await expect(modelSelect.locator('option[value="gpt-5.1-codex-2025-11-13"]')).toBeAttached();
    await expect(modelSelect.locator('option[value="gpt-5.1-codex-max-2025-12-04"]')).toBeAttached();

    // Verify the deployed model is selected
    await expect(modelSelect).toHaveValue("aaadp");
  });

  test("shows more than one model when Azure has many deployable models", async ({
    page,
  }) => {
    // The key bug was only 1 model showing. This proves multiple models render.
    const azureModels = [
      { id: "gpt-35-turbo", name: "gpt-35-turbo" },
      { id: "gpt-35-turbo-16k", name: "gpt-35-turbo-16k" },
      { id: "gpt-4", name: "gpt-4" },
      { id: "gpt-4-32k", name: "gpt-4-32k" },
      { id: "gpt-4o", name: "gpt-4o" },
      { id: "gpt-4o-mini", name: "gpt-4o-mini" },
      { id: "o1", name: "o1" },
      { id: "o1-mini", name: "o1-mini" },
      { id: "o1-preview", name: "o1-preview" },
      { id: "o3-mini", name: "o3-mini" },
      { id: "o4-mini", name: "o4-mini" },
    ];

    await mockProjectRoutes(page);
    await mockAzureLLMOptions(page, azureModels, "gpt-4o-mini");

    await page.goto("/project/proj-1");

    const modelSelect = page.locator('select[aria-label="LLM Model"]');
    await expect(modelSelect).toBeVisible();

    // Must have more than 1 model option (the original bug)
    const enabledOptions = modelSelect.locator("option:not([disabled])");
    const enabledCount = await enabledOptions.count();
    // subtract 1 for "Refresh models"
    expect(enabledCount - 1).toBeGreaterThan(1);
    expect(enabledCount - 1).toBe(azureModels.length);
  });

  test("active model is pre-selected in the dropdown", async ({
    page,
  }) => {
    const azureModels = [
      { id: "gpt-4o", name: "gpt-4o" },
      { id: "gpt-4o-mini", name: "gpt-4o-mini" },
      { id: "o4-mini", name: "o4-mini" },
    ];

    await mockProjectRoutes(page);
    await mockAzureLLMOptions(page, azureModels, "gpt-4o-mini");

    await page.goto("/project/proj-1");

    const modelSelect = page.locator('select[aria-label="LLM Model"]');
    await expect(modelSelect).toBeVisible();
    await expect(modelSelect).toHaveValue("gpt-4o-mini");
  });
});
