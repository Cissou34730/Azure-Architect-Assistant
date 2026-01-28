/**
 * Custom hook for proposal generation
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { proposalApi } from "../../../services/proposalService";
import { useToast } from "../../../hooks/useToast";

function closeEventSource(ref: React.RefObject<EventSource | null>): void {
  if (ref.current !== null) {
    try {
      ref.current.close();
    } catch {
      /* ignore */
    }
    ref.current = null;
  }
}

export const useProposal = () => {
  const eventSourceRef = useRef<EventSource | null>(null);
  const { error: showError } = useToast();
  const [architectureProposal, setArchitectureProposal] = useState("");
  const [proposalStage, setProposalStage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    return () => {
      closeEventSource(eventSourceRef);
    };
  }, []);

  const generateProposal = useCallback(
    (projectId: string, onComplete?: () => void) => {
      closeEventSource(eventSourceRef);

      setLoading(true);
      setProposalStage("Starting proposal generation...");

      const eventSource = proposalApi.createProposalStream(projectId, {
        onProgress: (params) => {
          setProposalStage(params.stage);
        },
        onComplete: (proposal) => {
          setArchitectureProposal(proposal);
          setProposalStage("Refreshing architecture sheet...");
          if (onComplete !== undefined) {
            onComplete();
          }
          setProposalStage("");
          setLoading(false);
          closeEventSource(eventSourceRef);
        },
        onError: (error) => {
          showError(error);
          setProposalStage("");
          setLoading(false);
          closeEventSource(eventSourceRef);
        },
      });

      eventSourceRef.current = eventSource;
    },
    [showError],
  );

  return {
    architectureProposal,
    proposalStage,
    loading,
    generateProposal,
  };
};
