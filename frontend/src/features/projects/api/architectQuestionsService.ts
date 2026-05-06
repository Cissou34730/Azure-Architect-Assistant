import { API_BASE } from "../../../shared/config/api";
import { fetchWithErrorHandling } from "../../../shared/http/fetchWithErrorHandling";

interface AnswerArchitectQuestionPayload {
  readonly status: "answered" | "deferred" | "not_applicable";
  readonly answer?: string;
  readonly answerSource?: string;
}

export const architectQuestionsApi = {
  async answer(
    projectId: string,
    questionId: string,
    payload: AnswerArchitectQuestionPayload,
  ): Promise<void> {
    await fetchWithErrorHandling<Record<string, unknown>>(
      `${API_BASE}/projects/${projectId}/architect-questions/${questionId}/answer`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
      "answer architect question",
    );
  },
};
