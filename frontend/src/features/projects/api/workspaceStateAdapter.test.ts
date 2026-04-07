import { describe, expect, it } from "vitest";
import type { ProjectWorkspaceView } from "../types/api-workspace";
import { workspaceToProjectState } from "./workspaceStateAdapter";

describe("workspaceToProjectState", () => {
  it("adapts the structured workspace payload into the ProjectState shape", () => {
    const workspace: ProjectWorkspaceView = {
      project: {
        id: "project-123",
        name: "Contoso Landing Zone",
        createdAt: "2026-04-01T10:00:00Z",
        textRequirements: "Build an Azure landing zone",
        documentCount: 2,
      },
      state: {
        lastUpdated: "2026-04-01T12:00:00Z",
        artifactKeys: ["requirements", "diagrams"],
      },
      inputs: {
        context: {
          summary: "Composed state",
          objectives: ["Secure by default"],
          targetUsers: "Platform team",
          scenarioType: "greenfield",
        },
        technicalConstraints: {
          constraints: ["Use Azure-native services"],
          assumptions: ["Hub-spoke network"],
        },
        openQuestions: ["What is the RTO?"],
      },
      documents: {
        items: [{ id: "doc-1", category: "uploaded", title: "Reference Architecture" }],
        stats: {
          attemptedDocuments: 1,
          parsedDocuments: 1,
          failedDocuments: 0,
          failures: [],
        },
      },
      artifacts: {
        requirements: [{ id: "req-1", text: "Keep behavior stable" }],
        assumptions: [{ id: "asm-1", text: "Existing hub network" }],
        clarificationQuestions: [{ id: "q-1", question: "Confirm residency" }],
        candidateArchitectures: [{ id: "candidate-1", title: "Option A" }],
        adrs: [],
        findings: [],
        diagrams: [
          {
            id: "diagram-1",
            diagramType: "c4-context",
            sourceCode: "graph TD;A-->B",
            version: "1.0.0",
            createdAt: "2026-04-01T11:00:00Z",
          },
        ],
        iacArtifacts: [],
        costEstimates: [],
        traceabilityLinks: [],
        traceabilityIssues: [],
        mindMapCoverage: { topics: {} },
        mindMap: { root: [] },
        mcpQueries: [],
        iterationEvents: [],
        analysisSummary: {
          runId: "run-1",
          startedAt: "2026-04-01T10:30:00Z",
          completedAt: "2026-04-01T10:35:00Z",
          status: "success",
          analyzedDocuments: 1,
          skippedDocuments: 0,
        },
        wafChecklist: { items: [] },
      },
      agent: { messageCount: 3, threadCount: 1, lastMessageAt: "2026-04-01T11:00:00Z" },
      checklists: [],
      knowledgeBases: [],
      diagrams: [],
      settings: { provider: "copilot", model: "gpt-5.4" },
    };

    expect(workspaceToProjectState(workspace)).toMatchObject({
      projectId: "project-123",
      lastUpdated: "2026-04-01T12:00:00Z",
      summary: "Composed state",
      objectives: ["Secure by default"],
      targetUsers: "Platform team",
      scenarioType: "greenfield",
      openQuestions: ["What is the RTO?"],
      requirements: [{ id: "req-1", text: "Keep behavior stable" }],
      assumptions: [{ id: "asm-1", text: "Existing hub network" }],
      clarificationQuestions: [{ id: "q-1", question: "Confirm residency" }],
      candidateArchitectures: [{ id: "candidate-1", title: "Option A" }],
      diagrams: [
        {
          id: "diagram-1",
          diagramType: "c4-context",
          sourceCode: "graph TD;A-->B",
          version: "1.0.0",
          createdAt: "2026-04-01T11:00:00Z",
        },
      ],
      referenceDocuments: [{ id: "doc-1", category: "uploaded", title: "Reference Architecture" }],
      projectDocumentStats: {
        attemptedDocuments: 1,
        parsedDocuments: 1,
        failedDocuments: 0,
        failures: [],
      },
      wafChecklist: { items: [] },
    });
  });
});