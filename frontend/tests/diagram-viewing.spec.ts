import { expect, test } from "@playwright/test";

const PROJECT_ID = "proj-1";

const mermaidDiagram = `graph TD
  A[Client] --> B[Load Balancer]
  B --> C[App Service]
  C --> D[SQL Database]`;

const projectStateWithDiagrams = {
  projectId: PROJECT_ID,
  context: { summary: "Architecture project", objectives: [], targetUsers: "", scenarioType: "" },
  technicalConstraints: { constraints: [], assumptions: [] },
  openQuestions: [],
  lastUpdated: "2026-01-15T10:00:00Z",
  requirements: [],
  assumptions: [],
  clarificationQuestions: [],
  candidateArchitectures: [],
  adrs: [],
  findings: [],
  diagrams: [
    {
      id: "diag-1",
      title: "Network Topology",
      diagramType: "architecture",
      sourceCode: mermaidDiagram,
      createdAt: "2026-01-15T10:00:00Z",
    },
    {
      id: "diag-2",
      title: "Data Flow Diagram",
      diagramType: "sequence",
      sourceCode: "sequenceDiagram\n  Client->>Server: Request\n  Server->>DB: Query\n  DB-->>Server: Result\n  Server-->>Client: Response",
      createdAt: "2026-01-15T11:00:00Z",
    },
  ],
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

function mockRoutes(page: import("@playwright/test").Page) {
  return Promise.all([
    page.route("**/api/projects", async (route) => {
      if (route.request().method() !== "GET") { await route.fallback(); return; }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ projects: [{ id: PROJECT_ID, name: "Arch Project" }] }),
      });
    }),
    page.route(`**/api/projects/${PROJECT_ID}`, async (route) => {
      if (route.request().method() !== "GET") { await route.fallback(); return; }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          project: { id: PROJECT_ID, name: "Arch Project", textRequirements: "", createdAt: "2026-01-15T10:00:00Z" },
        }),
      });
    }),
    page.route(`**/api/projects/${PROJECT_ID}/state`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ projectState: projectStateWithDiagrams }),
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
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
    }),
  ]);
}

test.describe("Diagram Viewing", () => {
  test("diagrams tab shows diagram titles", async ({ page }) => {
    await mockRoutes(page);
    await page.goto(`/project/${PROJECT_ID}`);

    const diagramsTab = page.getByRole("button", { name: /diagram/i });
    if (await diagramsTab.isVisible()) {
      await diagramsTab.click();
    } else {
      await page.goto(`/project/${PROJECT_ID}?tab=diagrams`);
    }

    await expect(page.getByText("Network Topology")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Data Flow Diagram")).toBeVisible();
  });

  test("diagram renders mermaid content without error", async ({ page }) => {
    await mockRoutes(page);
    await page.goto(`/project/${PROJECT_ID}?tab=diagrams`);

    await expect(page.getByText("Network Topology")).toBeVisible({ timeout: 10_000 });

    const errorBox = page.locator(".text-red-600, [role='alert']");
    const errorCount = await errorBox.count();
    expect(errorCount).toBe(0);
  });
});
