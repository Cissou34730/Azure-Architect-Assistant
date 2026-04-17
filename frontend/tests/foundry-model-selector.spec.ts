import { expect, test, type Page } from "@playwright/test";

interface MockModelIdentity { readonly id: string; readonly name: string; }

const PROJECT_ID = "proj-1";
const SIMPLE_FOUNDRY_MODELS: readonly MockModelIdentity[] = [
  { id: "gpt-35-turbo", name: "gpt-35-turbo" }, { id: "gpt-4", name: "gpt-4" },
  { id: "gpt-4o", name: "gpt-4o" }, { id: "gpt-4o-mini", name: "gpt-4o-mini" },
  { id: "o1-mini", name: "o1-mini" }, { id: "o1-preview", name: "o1-preview" }, { id: "o4-mini", name: "o4-mini" },
];
const COMPREHENSIVE_FOUNDRY_MODELS: readonly MockModelIdentity[] = [
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
  { id: "gpt-5.3-codex-2026-02-20", name: "gpt-5.3-codex-2026-02-20" }, { id: "gpt-5.3-chat-2026-03-03", name: "gpt-5.3-chat-2026-03-03" },
  { id: "gpt-5.4-nano-2026-03-17", name: "gpt-5.4-nano-2026-03-17" }, { id: "gpt-5.4-mini-2026-03-17", name: "gpt-5.4-mini-2026-03-17" },
  { id: "codex-mini-2025-05-16", name: "codex-mini-2025-05-16" }, { id: "o1-mini", name: "o1-mini" },
  { id: "o3-mini", name: "o3-mini" }, { id: "o4-mini", name: "o4-mini" },
];
const MULTI_DEPLOYMENT_FOUNDRY_MODELS: readonly MockModelIdentity[] = [
  { id: "gpt-35-turbo", name: "gpt-35-turbo" },
  { id: "gpt-35-turbo-16k", name: "gpt-35-turbo-16k" },
  { id: "gpt-4", name: "gpt-4" },
  { id: "gpt-4-32k", name: "gpt-4-32k" },
  { id: "gpt-4o", name: "gpt-4o" }, { id: "gpt-4o-mini", name: "gpt-4o-mini" },
  { id: "o1", name: "o1" }, { id: "o1-mini", name: "o1-mini" },
  { id: "o1-preview", name: "o1-preview" }, { id: "o3-mini", name: "o3-mini" }, { id: "o4-mini", name: "o4-mini" },
];

async function mockGetJson(page: Page, urlPattern: string, responseBody: object): Promise<void> {
  await page.route(urlPattern, async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(responseBody),
    });
  });
}

async function mockProjectRoutes(page: Page): Promise<void> {
  await Promise.all([
    mockGetJson(page, "**/api/projects", { projects: [{ id: PROJECT_ID, name: "Foundry Model Test" }] }),
    mockGetJson(page, `**/api/projects/${PROJECT_ID}`, {
      project: {
        id: PROJECT_ID,
        name: "Foundry Model Test",
        textRequirements: "",
        createdAt: "2026-03-27T00:00:00Z",
      },
    }),
    mockGetJson(page, `**/api/projects/${PROJECT_ID}/state`, {
      projectState: {
        projectId: PROJECT_ID,
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
    mockGetJson(page, `**/api/projects/${PROJECT_ID}/messages**`, { messages: [] }),
  ]);
}

function buildFoundryLLMOptions(foundryModels: readonly MockModelIdentity[], activeModel: string) {
  return {
    activeProvider: "foundry",
    activeModel,
    providers: [
      {
        id: "foundry",
        name: "Azure AI Foundry",
        status: "available",
        statusMessage: null,
        selected: true,
        models: foundryModels.map((foundryModel) => ({
          id: foundryModel.id,
          name: foundryModel.name,
          contextWindow: 128000,
          pricing: null,
        })),
        auth: null,
      },
    ],
  };
}

async function mockFoundryLLMOptions(page: Page, foundryModels: readonly MockModelIdentity[], activeModel: string): Promise<void> {
  await page.route("**/api/settings/llm-options**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(buildFoundryLLMOptions(foundryModels, activeModel)),
    });
  });
}

async function gotoProject(page: Page): Promise<void> {
  await page.goto(`/project/${PROJECT_ID}`);
}

async function expectFoundryProviderLabel(page: Page): Promise<void> {
  const providerSelect = page.locator('select[aria-label="LLM Provider"]');
  await expect(providerSelect).toBeVisible();
  await expect(providerSelect.locator('option[value="foundry"]')).toHaveText("Azure AI Foundry");
}

async function expectModelOptions(page: Page, foundryModels: readonly MockModelIdentity[]) {
  const modelSelect = page.locator('select[aria-label="LLM Model"]');
  await expect(modelSelect).toBeVisible();
  for (const foundryModel of foundryModels) {
    await expect(modelSelect.locator(`option[value="${foundryModel.id}"]`)).toBeAttached();
  }
  return modelSelect;
}

test("displays all Foundry chat-capable models in the dropdown", async ({ page }) => {
  await mockProjectRoutes(page);
  await mockFoundryLLMOptions(page, SIMPLE_FOUNDRY_MODELS, "gpt-4o-mini");
  await gotoProject(page);
  await expectFoundryProviderLabel(page);
  const modelSelect = await expectModelOptions(page, SIMPLE_FOUNDRY_MODELS);
  await expect(modelSelect.locator("option")).toHaveCount(SIMPLE_FOUNDRY_MODELS.length + 2);
});

test("displays the comprehensive Foundry model catalog", async ({ page }) => {
  await mockProjectRoutes(page);
  await mockFoundryLLMOptions(page, COMPREHENSIVE_FOUNDRY_MODELS, "aaadp");
  await gotoProject(page);
  await expectFoundryProviderLabel(page);
  const modelSelect = await expectModelOptions(page, COMPREHENSIVE_FOUNDRY_MODELS);
  await expect(modelSelect.locator('option[value="gpt-5.3-chat-2026-03-03"]')).toBeAttached();
  await expect(modelSelect.locator('option[value="gpt-5.3-codex-2026-02-20"]')).toBeAttached();
  await expect(modelSelect.locator('option[value="gpt-5.4-nano-2026-03-17"]')).toBeAttached();
  await expect(modelSelect.locator('option[value="gpt-5.4-mini-2026-03-17"]')).toBeAttached();
  await expect(modelSelect.locator('option[value="codex-mini-2025-05-16"]')).toBeAttached();
  await expect(modelSelect.locator('option[value="gpt-5-codex-2025-09-15"]')).toBeAttached();
  await expect(modelSelect.locator('option[value="gpt-5.1-codex-2025-11-13"]')).toBeAttached();
  await expect(modelSelect.locator('option[value="gpt-5.1-codex-max-2025-12-04"]')).toBeAttached();
  await expect(modelSelect).toHaveValue("aaadp");
});

test("shows multiple Foundry deployments when they are available", async ({ page }) => {
  await mockProjectRoutes(page);
  await mockFoundryLLMOptions(page, MULTI_DEPLOYMENT_FOUNDRY_MODELS, "gpt-4o-mini");
  await gotoProject(page);
  const modelSelect = await expectModelOptions(page, MULTI_DEPLOYMENT_FOUNDRY_MODELS);
  const enabledOptions = modelSelect.locator("option:not([disabled])");
  await expect(enabledOptions).toHaveCount(MULTI_DEPLOYMENT_FOUNDRY_MODELS.length + 1);
});

test("keeps the active Foundry model selected", async ({ page }) => {
  const activeFoundryModels = [{ id: "gpt-4o", name: "gpt-4o" }, { id: "gpt-4o-mini", name: "gpt-4o-mini" }, { id: "o4-mini", name: "o4-mini" }];
  await mockProjectRoutes(page);
  await mockFoundryLLMOptions(page, activeFoundryModels, "gpt-4o-mini");
  await gotoProject(page);
  const modelSelect = page.locator('select[aria-label="LLM Model"]');
  await expect(modelSelect).toBeVisible();
  await expect(modelSelect).toHaveValue("gpt-4o-mini");
});
