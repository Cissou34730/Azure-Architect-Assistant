/**
 * Custom hook for proposal generation
 */

import { useState, useCallback } from "react";
import { proposalApi } from "../services/apiService";

export const useProposal = () => {
  const [architectureProposal, setArchitectureProposal] = useState("");
  const [proposalStage, setProposalStage] = useState("");
  const [loading, setLoading] = useState(false);

  const generateProposal = useCallback(
    (projectId: string, onComplete?: () => void) => {
      setLoading(true);
      setProposalStage("Starting proposal generation...");

      const eventSource = proposalApi.createProposalStream(
        projectId,
        // onProgress
        (stage) => {
          setProposalStage(stage);
        },
        // onComplete
        (proposal) => {
          setArchitectureProposal(proposal);
          setProposalStage("Refreshing architecture sheet...");

          // Call completion callback
          if (onComplete) {
            onComplete();
          }

          setProposalStage("");
          setLoading(false);
        },
        // onError
        (error) => {
          alert(`Error: ${error}`);
          setProposalStage("");
          setLoading(false);
        }
      );

      // Return cleanup function
      return () => {
        eventSource.close();
        setProposalStage("");
        setLoading(false);
      };
    },
    []
  );

  return {
    architectureProposal,
    proposalStage,
    loading,
    generateProposal,
  };
};
