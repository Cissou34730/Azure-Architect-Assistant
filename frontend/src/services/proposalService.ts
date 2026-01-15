import { keysToCamel } from "../utils/apiMapping";
import { API_BASE } from "./config";

interface ProgressParams {
  readonly stage: string;
  readonly detail?: string;
}

interface ProposalOptions {
  readonly onProgress: (params: ProgressParams) => void;
  readonly onComplete: (proposal: string) => void;
  readonly onError: (error: string) => void;
}

interface ProposalEventData {
  readonly stage: string;
  readonly proposal?: string;
  readonly error?: string;
  readonly detail?: string;
}

const STAGE_MESSAGES: Record<string, string> = {
  started: "Initializing...",
  queryingWaf: "Querying Azure Well-Architected Framework...",
  queryingKnowledgeBases: "Querying knowledge bases...",
  buildingContext: "Building context from guidance...",
  generatingProposal: "Generating comprehensive proposal with AI...",
  finalizing: "Finalizing proposal...",
  completed: "Completed successfully",
};

export const proposalApi = {
  createProposalStream(
    projectId: string,
    options: ProposalOptions
  ): EventSource {
    const { onProgress, onComplete, onError } = options;
    const url = `${API_BASE}/projects/${projectId}/architecture/proposal`;
    const eventSource = new EventSource(url);

    eventSource.onmessage = (event: MessageEvent) => {
      try {
        if (typeof event.data !== "string") {
          return;
        }
        const data = keysToCamel<ProposalEventData>(JSON.parse(event.data));

        if (data.stage === "done") {
          onComplete(data.proposal ?? "");
          eventSource.close();
        } else if (data.stage === "error") {
          onError(data.error ?? "Unknown error");
          eventSource.close();
        } else {
          const stageMsg = STAGE_MESSAGES[data.stage];
          onProgress({
            stage:
              typeof stageMsg === "string" && stageMsg !== ""
                ? stageMsg
                : data.detail ?? "Processing...",
            detail: data.detail,
          });
        }
      } catch (error) {
        console.error("Error parsing SSE message:", error);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      onError("Connection error during proposal generation");
    };

    return eventSource;
  },
};
