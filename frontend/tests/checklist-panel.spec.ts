import { expect, test } from "@playwright/test";

const PROJECT_ID = "proj-1";
const CHECKLIST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

const emptyProjectState = {
  projectId: PROJECT_ID,
  context: { summary: "", objectives: [], targetUsers: "", scenarioType: "" },
  technicalConstraints: { constraints: [], assumptions: [] },
  openQuestions: [],
  lastUpdated: "2026-02-06T00:00:00Z",
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

const checklistWithItems = {
  id: CHECKLIST_ID,
  projectId: PROJECT_ID,
  templateId: null,
  templateSlug: "azure-waf-v1",
  title: "Azure WAF Review",
  status: "open",
  itemsCount: 3,
  lastSyncedAt: "2026-02-06T00:00:00Z",
  version: "2024",
  items: [
    {
      id: "item-1",
      templateItemId: "sec-01",
      title: "Enable MFA for all admin accounts",
      description: "Multi-factor authentication is a critical security control.",
      pillar: "Security",
      severity: "critical",
      guidance: null,
      itemMetadata: null,
      latestEvaluation: { status: "compliant", evaluator: "agent", timestamp: "2026-02-06T00:00:00Z" },
    },
    {
      id: "item-2",
      templateItemId: "rel-01",
      title: "Use availability zones",
      description: "Deploy across zones for resilience.",
      pillar: "Reliability",
      severity: "high",
      guidance: null,
      itemMetadata: null,
      latestEvaluation: { status: "non_compliant", evaluator: "agent", timestamp: "2026-02-06T00:00:00Z" },
    },
    {
      id: "item-3",
      templateItemId: "perf-01",
      title: "Use CDN for static content",
      description: null,
      pillar: "Performance Efficiency",
      severity: "medium",
      guidance: null,
      itemMetadata: null,
      latestEvaluation: null,
    },
  ],
};

function mockChecklistRoutes(page: import("@playwright/test").Page) {
  return Promise.all([
    page.route("**/api/projects", async (route) => {
      if (route.request().method() !== "GET") { await route.fallback(); return; }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ projects: [{ id: PROJECT_ID, name: "Checklist Project" }] }),
      });
    }),
    page.route(`**/api/projects/${PROJECT_ID}`, async (route) => {
      if (route.request().method() !== "GET") { await route.fallback(); return; }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          project: { id: PROJECT_ID, name: "Checklist Project", textRequirements: "", createdAt: "2026-02-06T00:00:00Z" },
        }),
      });
    }),
    page.route(`**/api/projects/${PROJECT_ID}/state`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ projectState: emptyProjectState }),
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
        body: JSON.stringify([{ id: CHECKLIST_ID }]),
      });
    }),
    page.route(`**/api/projects/${PROJECT_ID}/checklists/${CHECKLIST_ID}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(checklistWithItems),
      });
    }),
  ]);
}

test.describe("Checklist Panel", () => {
  test("WAF checklist tab shows all items by pillar", async ({ page }) => {
    await mockChecklistRoutes(page);
    await page.goto(`/project/${PROJECT_ID}`);

    const wafTab = page.getByRole("button", { name: /waf/i });
    if (await wafTab.isVisible()) {
      await wafTab.click();
    } else {
      await page.goto(`/project/${PROJECT_ID}?tab=waf`);
    }

    await expect(page.getByText("Enable MFA for all admin accounts")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Use availability zones")).toBeVisible();
    await expect(page.getByText("Use CDN for static content")).toBeVisible();
  });

  test("checklist shows pillar labels", async ({ page }) => {
    await mockChecklistRoutes(page);
    await page.goto(`/project/${PROJECT_ID}`);

    const wafTab = page.getByRole("button", { name: /waf/i });
    if (await wafTab.isVisible()) {
      await wafTab.click();
    } else {
      await page.goto(`/project/${PROJECT_ID}?tab=waf`);
    }

    await expect(page.getByText("Security")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Reliability")).toBeVisible();
  });

  test("empty checklist shows placeholder", async ({ page }) => {
    await page.route("**/api/projects", async (route) => {
      if (route.request().method() !== "GET") { await route.fallback(); return; }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ projects: [{ id: PROJECT_ID, name: "Empty Project" }] }),
      });
    });
    await page.route(`**/api/projects/${PROJECT_ID}`, async (route) => {
      if (route.request().method() !== "GET") { await route.fallback(); return; }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          project: { id: PROJECT_ID, name: "Empty Project", textRequirements: "", createdAt: "2026-02-06T00:00:00Z" },
        }),
      });
    });
    await page.route(`**/api/projects/${PROJECT_ID}/state`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ projectState: emptyProjectState }),
      });
    });
    await page.route(`**/api/projects/${PROJECT_ID}/messages**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ messages: [] }),
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
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.goto(`/project/${PROJECT_ID}`);

    const wafTab = page.getByRole("button", { name: /waf/i });
    if (await wafTab.isVisible()) {
      await wafTab.click();
    } else {
      await page.goto(`/project/${PROJECT_ID}?tab=waf`);
    }

    // With no checklist, expect some kind of empty state
    await expect(
      page.getByText(/no checklist|no items|empty|create.*checklist/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });
});
