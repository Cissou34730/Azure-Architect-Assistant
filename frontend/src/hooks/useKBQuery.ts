import { useState } from "react";
import { kbApi } from "../services/kbService";
import { KbQueryResponse } from "../types/api";
import { useToast } from "./useToast";

export function useKBQuery() {
  const { error: showError } = useToast();
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<KbQueryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const submitQuery = async (
    e?: React.FormEvent,
    kbIds?: readonly string[]
  ) => {
    if (e !== undefined) e.preventDefault();
    const queryText = question.trim();
    if (queryText === "") return;

    setIsLoading(true);
    setResponse(null);

    try {
      let data: KbQueryResponse;

      if (kbIds !== undefined && kbIds.length > 0) {
        // Manual KB selection
        data = await kbApi.queryKBs(queryText, kbIds, 5);
      } else {
        // Legacy query (fallback)
        data = await kbApi.query(queryText, 3);
      }

      setResponse(data);
    } catch (error) {
      console.error("Error querying knowledge bases:", error);
      showError("Error querying knowledge bases");
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
