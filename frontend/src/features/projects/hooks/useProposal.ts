/**
 * Custom hook for proposal generation
 */

import { useState, useCallback } from "react";
import { proposalApi } from "../../../services/proposalService";
import { useToast } from "../../../hooks/useToast";

export const useProposal = () => {
  const { error: showError } = useToast();
  const [architectureProposal, setArchitectureProposal] = useState("");
  const [proposalStage, setProposalStage] = useState("");
  const [loading, setLoading] = useState(false);

  const generateProposal = useCallback(
    (projectId: string, onComplete?: () => void) => {
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
        },
        onError: (error) => {
          showError(error);
          setProposalStage("");
          setLoading(false);
        },
      });

      // Return cleanup function
      return () => {
        eventSource.close();
        setProposalStage("");
        setLoading(false);
      };
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
