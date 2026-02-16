import { expect, test } from "@playwright/test";

function buildProjectState() {
  return {
    projectId: "proj-1",
    context: {
      summary: "",
      objectives: [],
      targetUsers: "",
      scenarioType: "",
    },
    technicalConstraints: {
      constraints: [],
      assumptions: [],
    },
    openQuestions: [],
    lastUpdated: new Date().toISOString(),
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
    referenceDocuments: [
      {
        id: "doc-1",
        category: "uploaded",
        title: "requirements.txt",
        accessedAt: new Date().toISOString(),
        parseStatus: "parsed",
        analysisStatus: "analyzed",
      },
      {
        id: "doc-2",
        category: "uploaded",
        title: "legacy.bin",
        accessedAt: new Date().toISOString(),
        parseStatus: "parse_failed",
        analysisStatus: "skipped",
        parseError: "unsupported format",
      },
    ],
    mcpQueries: [],
    projectDocumentStats: {
      attemptedDocuments: 2,
      parsedDocuments: 1,
      failedDocuments: 1,
      failures: [
        {
          documentId: "doc-2",
          fileName: "legacy.bin",
          reason: "unsupported format",
        },
      ],
    },
    analysisSummary: {
      runId: "run-1",
      startedAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
      status: "success",
      analyzedDocuments: 1,
      skippedDocuments: 1,
    },
    iterationEvents: [],
  };
}

test("initialization setup is visible and upload action is single-source", async ({
  page,
}) => {
  const state = buildProjectState();

  await page.route("**/api/projects", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        projects: [{ id: "proj-1", name: "Init Flow Project" }],
      }),
    });
  });

  await page.route("**/api/projects/proj-1", async (route) => {
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
          name: "Init Flow Project",
          textRequirements: "",
          createdAt: new Date().toISOString(),
        },
      }),
    });
  });

  await page.route("**/api/projects/proj-1/state", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ projectState: state }),
    });
  });

  await page.route("**/api/projects/proj-1/messages**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ messages: [] }),
    });
  });

  await page.goto("/project/proj-1");

  await expect(page.getByText("Initialization Setup")).toBeVisible();
  await expect(page.getByText("Step D - Setup Complete")).toBeVisible();
  await expect(page.getByText("Upload Summary")).toBeVisible();
  await expect(page.getByText("Analysis Summary")).toBeVisible();
  await expect(page.getByRole("button", { name: /^Upload$/ })).toHaveCount(1);

  await page.getByText("requirements.txt").first().click();
  await expect(
    page.getByRole("heading", { name: "requirements.txt" }),
  ).toBeVisible();
  await expect(page.getByText("Parse status: parsed")).toBeVisible();
});
