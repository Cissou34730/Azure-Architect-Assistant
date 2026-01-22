/**
 * Custom hook for proposal generation
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { proposalApi } from "../../../services/proposalService";
import { useToast } from "../../../hooks/useToast";

export const useProposal = () => {
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => {
      // cleanup on unmount
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, []);

  const { error: showError } = useToast();
  const [architectureProposal, setArchitectureProposal] = useState("");
  const [proposalStage, setProposalStage] = useState("");
  const [loading, setLoading] = useState(false);

  const generateProposal = useCallback(
    (projectId: string, onComplete?: () => void) => {
      // close any existing stream before starting a new one
      if (eventSourceRef.current) {
        try {
          eventSourceRef.current.close();
        } catch {
          /* ignore */
        }
        eventSourceRef.current = null;
      }

      setLoading(true);
      setProposalStage("Starting proposal generation...");

      const eventSource = proposalApi.createProposalStream(projectId, {
        onProgress: (params) => {
          setProposalStage(params.stage);
        },
        onComplete: (proposal) => {
          setArchitectureProposal(proposal);
          setProposalStage("Refreshing architecture sheet...");
          if (onComplete) {
            onComplete();
          }
          setProposalStage("");
          setLoading(false);
          // close and clear ref when done
          if (eventSourceRef.current) {
            try {
              eventSourceRef.current.close();
            } catch {
              /* ignore */
            }
            eventSourceRef.current = null;
          }
        },
        onError: (error) => {
          showError(error);
          setProposalStage("");
          setLoading(false);
          if (eventSourceRef.current) {
            try {
              eventSourceRef.current.close();
            } catch {
              /* ignore */
            }
            eventSourceRef.current = null;
          }
        },
      });

      // store ref for possible external control (cleanup on unmount)
      eventSourceRef.current = eventSource;
    },
    [showError]
  );

  return {
    architectureProposal,
    proposalStage,
    loading,
    generateProposal,
  };
};
