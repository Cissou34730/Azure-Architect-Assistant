import { render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QualityGateTab } from "./QualityGateTab";
import { qualityGateApi } from "../../api/qualityGateService";

vi.mock("../../api/qualityGateService", () => ({
  qualityGateApi: {
    get: vi.fn(),
  },
}));

describe("QualityGateTab", () => {
  it("renders the backend quality-gate report sections", async () => {
    vi.mocked(qualityGateApi.get).mockResolvedValue({
      generatedAt: "2026-04-17T10:00:00Z",
      waf: {
        totalItems: 3,
        coveredItems: 1,
        partialItems: 1,
        notCoveredItems: 1,
        coveragePercentage: 50,
        pillars: [
          {
            pillar: "Reliability",
            totalItems: 2,
            coveredItems: 1,
            partialItems: 1,
            notCoveredItems: 0,
            coveragePercentage: 75,
          },
        ],
      },
      mindMap: {
        totalTopics: 13,
        addressedTopics: 8,
        partialTopics: 2,
        notAddressedTopics: 3,
        coveragePercentage: 69,
        topics: [
          {
            key: "1_foundations",
            label: "Foundations",
            status: "addressed",
            confidence: 1,
          },
          {
            key: "2_compute",
            label: "Compute",
            status: "partial",
            confidence: 0.5,
          },
        ],
      },
      openClarifications: {
        count: 1,
        items: [
          {
            id: "q-1",
            question: "Confirm the secondary failover region.",
            status: "open",
            priority: 1,
          },
        ],
      },
      missingArtifacts: {
        count: 2,
        items: [
          {
            key: "adrs",
            label: "ADRs",
            reason: "No architecture decisions have been recorded yet.",
          },
          {
            key: "iac",
            label: "Infrastructure as Code",
            reason: "No IaC artifact has been generated yet.",
          },
        ],
      },
      trace: {
        totalEvents: 3,
        lastEventAt: "2026-04-17T10:05:00Z",
        eventTypes: [
          { eventType: "state_updated", count: 2 },
          { eventType: "messages_persisted", count: 1 },
        ],
      },
    });

    render(<QualityGateTab projectId="project-123" lastUpdated="2026-04-17T10:00:00Z" />);

    expect(await screen.findByText(/quality gate report/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/waf coverage/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/mindmap coverage/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/open clarifications/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/missing artifacts/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/recent trace activity/i)).toBeInTheDocument();
    expect(screen.getByText(/confirm the secondary failover region/i)).toBeInTheDocument();
    expect(screen.getByText(/state_updated/i)).toBeInTheDocument();

    const wafSection = screen.getByLabelText(/waf coverage/i);
    expect(within(wafSection).getByText(/50%/i)).toBeInTheDocument();
    expect(within(wafSection).getByText(/reliability/i)).toBeInTheDocument();

    const missingArtifactsSection = screen.getByLabelText(/missing artifacts/i);
    expect(within(missingArtifactsSection).getByText(/^adrs$/i)).toBeInTheDocument();
    expect(
      within(missingArtifactsSection).getByText(/infrastructure as code/i),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(qualityGateApi.get).toHaveBeenCalledWith("project-123");
    });
  });
});
