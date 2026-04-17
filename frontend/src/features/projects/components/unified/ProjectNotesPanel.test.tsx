import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ProjectNotesPanel } from "./ProjectNotesPanel";
import { projectNotesApi } from "../../api/projectNotesService";

vi.mock("../../api/projectNotesService", () => ({
  projectNotesApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  },
}));

describe("ProjectNotesPanel", () => {
  it("loads notes and creates a new note", async () => {
    const list = vi.mocked(projectNotesApi.list);
    const create = vi.mocked(projectNotesApi.create);

    list.mockResolvedValue({
      notes: [
        {
          id: "note-1",
          projectId: "project-123",
          category: "decision",
          content: "Use hub-spoke networking.",
          sourceMessageId: null,
          createdAt: "2026-04-17T10:00:00Z",
          updatedAt: "2026-04-17T10:00:00Z",
        },
      ],
    });
    create.mockResolvedValue({
      note: {
        id: "note-2",
        projectId: "project-123",
        category: "risk",
        content: "Run a DR rehearsal before sign-off.",
        sourceMessageId: null,
        createdAt: "2026-04-17T11:00:00Z",
        updatedAt: "2026-04-17T11:00:00Z",
      },
    });

    render(<ProjectNotesPanel projectId="project-123" />);

    expect(await screen.findByText(/use hub-spoke networking/i)).toBeTruthy();

    await userEvent.selectOptions(screen.getByLabelText(/category/i), "risk");
    await userEvent.type(
      screen.getByLabelText(/note content/i),
      "Run a DR rehearsal before sign-off.",
    );
    await userEvent.click(screen.getByRole("button", { name: /add note/i }));

    await waitFor(() => {
      expect(create).toHaveBeenCalledWith("project-123", {
        category: "risk",
        content: "Run a DR rehearsal before sign-off.",
        sourceMessageId: null,
      });
    });
  });
});
