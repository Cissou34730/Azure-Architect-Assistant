import { expect, test } from "@playwright/test";

const PROJECT_ID = "proj-1";

const projectStateWithDocs = {
  projectId: PROJECT_ID,
  context: { summary: "", objectives: [], targetUsers: "", scenarioType: "" },
  technicalConstraints: { constraints: [], assumptions: [] },
  openQuestions: [],
  lastUpdated: "2026-01-20T10:00:00Z",
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
  referenceDocuments: [
    {
      id: "doc-1",
      category: "uploaded",
      title: "architecture-spec.pdf",
      accessedAt: "2026-01-20T10:00:00Z",
      parseStatus: "parsed",
      analysisStatus: "analyzed",
    },
    {
      id: "doc-2",
      category: "uploaded",
      title: "requirements.docx",
      accessedAt: "2026-01-20T11:00:00Z",
      parseStatus: "parsed",
      analysisStatus: "analyzed",
    },
    {
      id: "doc-3",
      category: "uploaded",
      title: "corrupted.bin",
      accessedAt: "2026-01-20T12:00:00Z",
      parseStatus: "parse_failed",
      analysisStatus: "skipped",
      parseError: "Unsupported file format",
    },
  ],
  mcpQueries: [],
  projectDocumentStats: {
    attemptedDocuments: 3,
    parsedDocuments: 2,
    failedDocuments: 1,
    failures: [{ documentId: "doc-3", fileName: "corrupted.bin", reason: "Unsupported file format" }],
  },
  analysisSummary: {
    runId: "run-1",
    startedAt: "2026-01-20T10:00:00Z",
    completedAt: "2026-01-20T10:05:00Z",
    status: "success",
    analyzedDocuments: 2,
    skippedDocuments: 1,
  },
  iterationEvents: [],
};

function mockRoutes(page: import("@playwright/test").Page) {
  return Promise.all([
    page.route("**/api/projects", async (route) => {
      if (route.request().method() !== "GET") { await route.fallback(); return; }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ projects: [{ id: PROJECT_ID, name: "Doc Upload Project" }] }),
      });
    }),
    page.route(`**/api/projects/${PROJECT_ID}`, async (route) => {
      if (route.request().method() !== "GET") { await route.fallback(); return; }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          project: { id: PROJECT_ID, name: "Doc Upload Project", textRequirements: "", createdAt: "2026-01-20T10:00:00Z" },
        }),
      });
    }),
    page.route(`**/api/projects/${PROJECT_ID}/state`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ projectState: projectStateWithDocs }),
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

test.describe("Document Upload", () => {
  test("input overview shows uploaded documents with parse status", async ({ page }) => {
    await mockRoutes(page);
    await page.goto(`/project/${PROJECT_ID}`);

    // Input overview is the default tab
    await expect(page.getByText("architecture-spec.pdf")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("requirements.docx")).toBeVisible();
  });

  test("failed document is visible with error indication", async ({ page }) => {
    await mockRoutes(page);
    await page.goto(`/project/${PROJECT_ID}`);

    await expect(page.getByText("corrupted.bin")).toBeVisible({ timeout: 10_000 });
    // Either a "failed" badge, red styling, or the error reason should be visible
    const failedIndicator = page.getByText(/failed|error|unsupported/i);
    await expect(failedIndicator.first()).toBeVisible();
  });

  test("upload button is visible on input overview tab", async ({ page }) => {
    await mockRoutes(page);
    await page.goto(`/project/${PROJECT_ID}`);

    const uploadButton = page.getByRole("button", { name: /upload/i });
    await expect(uploadButton.first()).toBeVisible({ timeout: 10_000 });
  });
});
