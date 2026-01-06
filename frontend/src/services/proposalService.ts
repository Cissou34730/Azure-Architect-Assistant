const API_BASE = `${
  import.meta.env.BACKEND_URL || "http://localhost:8000"
}/api`;

export const proposalApi = {
  createProposalStream(
    projectId: string,
    onProgress: (stage: string, detail?: string) => void,
    onComplete: (proposal: string) => void,
    onError: (error: string) => void
  ): EventSource {
    const url = `${API_BASE}/proposals/${projectId}/stream`;
    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "progress") {
          onProgress(data.stage, data.detail);
        } else if (data.type === "complete") {
          onComplete(data.proposal || "");
          eventSource.close();
        } else if (data.type === "error") {
          onError(data.error);
          eventSource.close();
        }
      } catch (e) {
        console.error("Error parsing SSE data:", e);
      }
    };

    eventSource.onerror = () => {
      onError("Connection failed");
      eventSource.close();
    };

    return eventSource;
  },
};
