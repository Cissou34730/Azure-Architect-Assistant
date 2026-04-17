import { API_BASE } from "../../../shared/config/api";
import { fetchWithErrorHandling } from "../../../shared/http/fetchWithErrorHandling";

export type ProjectNoteCategory = "decision" | "context" | "question" | "risk";

export interface ProjectNote {
  readonly id: string;
  readonly projectId: string;
  readonly category: ProjectNoteCategory;
  readonly content: string;
  readonly sourceMessageId: string | null;
  readonly createdAt: string;
  readonly updatedAt: string;
}

export interface ProjectNotesResponse {
  readonly notes: readonly ProjectNote[];
}

export interface ProjectNoteResponse {
  readonly note: ProjectNote;
}

export interface DeleteProjectNoteResponse {
  readonly deleted: boolean;
  readonly noteId: string;
}

export interface ProjectNoteUpsertRequest {
  readonly category: ProjectNoteCategory;
  readonly content: string;
  readonly sourceMessageId: string | null;
}

export const projectNotesApi = {
  async list(projectId: string): Promise<ProjectNotesResponse> {
    return fetchWithErrorHandling<ProjectNotesResponse>(
      `${API_BASE}/projects/${projectId}/notes`,
      {},
      "list project notes",
    );
  },

  async create(
    projectId: string,
    request: ProjectNoteUpsertRequest,
  ): Promise<ProjectNoteResponse> {
    return fetchWithErrorHandling<ProjectNoteResponse>(
      `${API_BASE}/projects/${projectId}/notes`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      },
      "create project note",
    );
  },

  async update(
    projectId: string,
    noteId: string,
    request: ProjectNoteUpsertRequest,
  ): Promise<ProjectNoteResponse> {
    return fetchWithErrorHandling<ProjectNoteResponse>(
      `${API_BASE}/projects/${projectId}/notes/${noteId}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      },
      "update project note",
    );
  },

  async remove(projectId: string, noteId: string): Promise<DeleteProjectNoteResponse> {
    return fetchWithErrorHandling<DeleteProjectNoteResponse>(
      `${API_BASE}/projects/${projectId}/notes/${noteId}`,
      { method: "DELETE" },
      "delete project note",
    );
  },
};
