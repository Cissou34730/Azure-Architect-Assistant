import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TraceTab } from "./TraceTab";
import { traceApi } from "../../api/traceService";

vi.mock("../../api/traceService", () => ({
  traceApi: {
    list: vi.fn(),
  },
}));

describe("TraceTab", () => {
  it("renders a workflow trace timeline from backend events", async () => {
    vi.mocked(traceApi.list).mockResolvedValue({
      events: [
        {
          id: "evt-1",
          projectId: "project-123",
          threadId: "thread-1",
          eventType: "workflow_stage_result",
          payload: {
            stage: "propose_candidate",
            changeSetId: "pcs-1",
            evidence: [{ title: "Retail Prices sample" }],
          },
          createdAt: "2026-04-17T10:00:00Z",
        },
        {
          id: "evt-2",
          projectId: "project-123",
          threadId: "thread-1",
          eventType: "state_updated",
          payload: {
            stage: "manage_adr",
            update_keys: ["requirements", "adrs"],
          },
          createdAt: "2026-04-17T10:01:00Z",
        },
      ],
    });

    render(<TraceTab projectId="project-123" lastUpdated="2026-04-17T10:01:00Z" />);

    expect(await screen.findByText(/workflow trace/i)).toBeInTheDocument();
    expect(screen.getByText(/stage classification/i)).toBeInTheDocument();
    expect(screen.getByText(/state updates/i)).toBeInTheDocument();
    expect(screen.getByText(/propose_candidate/i)).toBeInTheDocument();
    expect(screen.getByText(/requirements, adrs/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(traceApi.list).toHaveBeenCalledWith("project-123");
    });
  });
});
