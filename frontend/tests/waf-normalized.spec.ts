import { expect, test } from "@playwright/test";

const PROJECT_ID = "proj-1";
const CHECKLIST_ID = "11111111-1111-1111-1111-111111111111";

const emptyProjectState = {
  projectId: PROJECT_ID,
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
  lastUpdated: "2026-02-06T00:00:00Z",
  requirements: [],
  assumptions: [],
  clarificationQuestions: [],
  candidateArchitectures: [],
  adrs: [],
  wafChecklist: {
    version: "1",
    pillars: [],
    items: [],
  },
  findings: [],
  diagrams: [],
  iacArtifacts: [],
  costEstimates: [],
  traceabilityLinks: [],
  mindMapCoverage: { topics: {} },
  traceabilityIssues: [],
  mindMap: {},
  referenceDocuments: [],
  mcpQueries: [],
  iterationEvents: [],
};

test("waf tab renders normalized checklist data when legacy state is empty", async ({ page }) => {
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const method = request.method();
    const url = request.url();

    if (method !== "GET") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
      return;
    }

    if (url.endsWith("/api/projects")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ projects: [{ id: PROJECT_ID, name: "Demo Project" }] }),
      });
      return;
    }

    if (url.endsWith(`/api/projects/${PROJECT_ID}`)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          project: {
            id: PROJECT_ID,
            name: "Demo Project",
            textRequirements: "",
            createdAt: "2026-02-06T00:00:00Z",
          },
        }),
      });
      return;
    }

    if (url.endsWith(`/api/projects/${PROJECT_ID}/state`)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ projectState: emptyProjectState }),
      });
      return;
    }

    if (url.includes(`/api/projects/${PROJECT_ID}/messages`)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ messages: [] }),
      });
      return;
    }

    if (url.endsWith(`/api/projects/${PROJECT_ID}/checklists`)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([{ id: CHECKLIST_ID }]),
      });
      return;
    }

    if (url.endsWith(`/api/projects/${PROJECT_ID}/checklists/${CHECKLIST_ID}`)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: CHECKLIST_ID,
          projectId: PROJECT_ID,
          templateId: null,
          templateSlug: "azure-waf-v1",
          title: "Azure WAF",
          status: "open",
          itemsCount: 2,
          lastSyncedAt: "2026-02-06T00:00:00Z",
          version: "2024",
          items: [
            {
              id: "22222222-2222-2222-2222-222222222222",
              templateItemId: "security-1",
              title: "Use Azure RBAC",
              description: null,
              pillar: "Security",
              severity: "critical",
              guidance: null,
              itemMetadata: null,
              latestEvaluation: {
                status: "in_progress",
                evaluator: "agent",
                timestamp: "2026-02-06T00:00:00Z",
              },
            },
            {
              id: "33333333-3333-3333-3333-333333333333",
              templateItemId: "reliability-1",
              title: "Design for high availability",
              description: null,
              pillar: "Reliability",
              severity: "high",
              guidance: null,
              itemMetadata: null,
              latestEvaluation: null,
            },
          ],
        }),
      });
      return;
    }

    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
  });

  await page.goto(`/project/${PROJECT_ID}`);
  await page.getByRole("button", { name: "WAF Checklist" }).click();

  await expect(page.getByText("Use Azure RBAC")).toBeVisible();
  await expect(page.getByText("Design for high availability")).toBeVisible();
  await expect(page.getByText("No checklist items available.")).toHaveCount(0);
});
