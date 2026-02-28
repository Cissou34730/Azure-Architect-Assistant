import { expect, test } from "@playwright/test";

const PROJECT_ID = "proj-1";

const projectState = {
  projectId: PROJECT_ID,
  context: { summary: "Contoso migration to Azure", objectives: ["Lift & shift"], targetUsers: "IT team", scenarioType: "migration" },
  technicalConstraints: { constraints: [], assumptions: [] },
  openQuestions: [],
  lastUpdated: "2026-01-15T10:00:00Z",
  requirements: [],
  assumptions: [],
  clarificationQuestions: [],
  candidateArchitectures: [],
  adrs: [],
  wafChecklist: { version: "1", pillars: [], items: [] },
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
};

function mockProjectRoutes(page: import("@playwright/test").Page) {
  return Promise.all([
    page.route("**/api/projects", async (route) => {
      if (route.request().method() !== "GET") { await route.fallback(); return; }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ projects: [{ id: PROJECT_ID, name: "Contoso Migration" }] }),
      });
    }),
    page.route(`**/api/projects/${PROJECT_ID}`, async (route) => {
      if (route.request().method() !== "GET") { await route.fallback(); return; }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          project: { id: PROJECT_ID, name: "Contoso Migration", textRequirements: "", createdAt: "2026-01-15T10:00:00Z" },
        }),
      });
    }),
    page.route(`**/api/projects/${PROJECT_ID}/state`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ projectState }),
      });
    }),
    page.route(`**/api/projects/${PROJECT_ID}/messages**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ messages: [] }),
      });
    }),
    page.route("**/api/agent/health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "healthy", mcpClientConnected: true, openaiConfigured: true }),
      });
    }),
    page.route(`**/api/projects/${PROJECT_ID}/checklists`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    }),
  ]);
}

test.describe("Agent Chat", () => {
  test("chat panel renders with empty conversation and send is disabled", async ({ page }) => {
    await mockProjectRoutes(page);
    await page.goto(`/project/${PROJECT_ID}`);

    const chatPanel = page.locator("[data-testid='chat-panel'], .agent-chat-panel").first();
    await expect(chatPanel.or(page.getByText("Start a conversation"))).toBeVisible();

    const sendButton = page.getByRole("button", { name: /send/i });
    if (await sendButton.isVisible()) {
      await expect(sendButton).toBeDisabled();
    }
  });

  test("sending a message shows user bubble and assistant reply", async ({ page }) => {
    await mockProjectRoutes(page);

    await page.route(`**/api/agent/projects/${PROJECT_ID}/chat`, async (route) => {
      if (route.request().method() !== "POST") { await route.fallback(); return; }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          answer: "I recommend Azure App Service for the Contoso migration.",
          success: true,
          reasoningSteps: [
            { action: "AnalyzeRequirements", actionInput: "migration", observation: "Lift & shift scenario" },
          ],
        }),
      });
    });

    await page.goto(`/project/${PROJECT_ID}`);

    const textarea = page.getByRole("textbox").first();
    await textarea.fill("What Azure service should we use?");

    const sendButton = page.getByRole("button", { name: /send/i });
    await sendButton.click();

    await expect(page.getByText("What Azure service should we use?")).toBeVisible();
    await expect(page.getByText("I recommend Azure App Service for the Contoso migration.")).toBeVisible({ timeout: 10_000 });
  });

  test("conversation history loads existing messages", async ({ page }) => {
    await page.route("**/api/projects", async (route) => {
      if (route.request().method() !== "GET") { await route.fallback(); return; }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ projects: [{ id: PROJECT_ID, name: "Contoso Migration" }] }),
      });
    });
    await page.route(`**/api/projects/${PROJECT_ID}`, async (route) => {
      if (route.request().method() !== "GET") { await route.fallback(); return; }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          project: { id: PROJECT_ID, name: "Contoso Migration", textRequirements: "", createdAt: "2026-01-15T10:00:00Z" },
        }),
      });
    });
    await page.route(`**/api/projects/${PROJECT_ID}/state`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ projectState }),
      });
    });
    await page.route(`**/api/projects/${PROJECT_ID}/messages**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          messages: [
            { id: "msg-1", role: "user", content: "How do I migrate the database?" },
            { id: "msg-2", role: "assistant", content: "Use Azure Database Migration Service." },
          ],
        }),
      });
    });
    await page.route("**/api/agent/health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "healthy", mcpClientConnected: true, openaiConfigured: true }),
      });
    });
    await page.route(`**/api/projects/${PROJECT_ID}/checklists`, async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
    });

    await page.goto(`/project/${PROJECT_ID}`);

    await expect(page.getByText("How do I migrate the database?")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Use Azure Database Migration Service.")).toBeVisible();
  });
});
