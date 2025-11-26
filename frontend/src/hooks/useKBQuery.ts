import { useState } from "react";
import { kbApi, KBQueryResponse } from "../services/apiService";

export function useKBQuery() {
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<KBQueryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const submitQuery = async (e?: React.FormEvent, kbIds?: string[]) => {
    if (e) e.preventDefault();
    if (!question.trim()) return;

    setIsLoading(true);
    setResponse(null);

    try {
      let data: KBQueryResponse;

      if (kbIds && kbIds.length > 0) {
        // Manual KB selection
        data = await kbApi.queryKBs(question.trim(), kbIds, 5);
      } else {
        // Legacy query (fallback)
        data = await kbApi.query(question.trim(), 3);
      }

      setResponse(data);
    } catch (error) {
      console.error("Error querying knowledge bases:", error);
      alert("Error querying knowledge bases");
    } finally {
      setIsLoading(false);
    }
  };

  const askFollowUp = (followUpQuestion: string) => {
    setQuestion(followUpQuestion);
  };

  return {
    question,
    setQuestion,
    response,
    isLoading,
    submitQuery,
    askFollowUp,
  };
}
