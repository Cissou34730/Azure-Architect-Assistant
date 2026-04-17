import { useCallback, useEffect, useState } from "react";
import { pendingChangesApi } from "../api/pendingChangesService";
import type { PendingChangeDetail, PendingChangeSummary } from "../types/pending-changes";

interface UsePendingChangeReviewArgs {
  readonly projectId: string;
  readonly pendingChangeSignalId?: string;
  readonly onRefreshProjectState: () => Promise<void>;
  readonly onRefreshMessages: () => Promise<void>;
}

// eslint-disable-next-line max-lines-per-function -- The review hook owns one cohesive pending-change workflow for the chat rail.
export function usePendingChangeReview({
  projectId,
  pendingChangeSignalId,
  onRefreshProjectState,
  onRefreshMessages,
}: UsePendingChangeReviewArgs) {
  const [isPendingChangesVisible, setIsPendingChangesVisible] = useState(false);
  const [pendingChangeSummaries, setPendingChangeSummaries] = useState<
    readonly PendingChangeSummary[]
  >([]);
  const [selectedPendingChange, setSelectedPendingChange] =
    useState<PendingChangeDetail | null>(null);
  const [reviewReason, setReviewReason] = useState("");
  const [isPendingChangesLoading, setIsPendingChangesLoading] = useState(false);
  const [reviewActionInFlight, setReviewActionInFlight] = useState<
    "approve" | "reject" | null
  >(null);

  const loadPendingChanges = useCallback(async () => {
    setIsPendingChangesLoading(true);
    try {
      const nextPendingChangeSummaries = await pendingChangesApi.list(projectId, {
        status: "pending",
      });
      setPendingChangeSummaries(nextPendingChangeSummaries);

      const nextSelectedChangeId =
        pendingChangeSignalId ?? nextPendingChangeSummaries.at(0)?.id ?? null;
      if (nextSelectedChangeId === null) {
        setSelectedPendingChange(null);
        return;
      }

      const pendingChangeDetail = await pendingChangesApi.get(
        projectId,
        nextSelectedChangeId,
      );
      setSelectedPendingChange(pendingChangeDetail);
    } finally {
      setIsPendingChangesLoading(false);
    }
  }, [pendingChangeSignalId, projectId]);

  useEffect(() => {
    if (pendingChangeSignalId !== undefined) {
      setIsPendingChangesVisible(true);
    }
  }, [pendingChangeSignalId]);

  useEffect(() => {
    if (!isPendingChangesVisible) {
      return;
    }

    void loadPendingChanges();
  }, [isPendingChangesVisible, loadPendingChanges]);

  const reviewPendingChange = useCallback(
    async (reviewAction: "approve" | "reject") => {
      if (selectedPendingChange === null) {
        return;
      }

      setReviewActionInFlight(reviewAction);
      try {
        if (reviewAction === "approve") {
          await pendingChangesApi.approve(projectId, selectedPendingChange.id, null);
        } else {
          await pendingChangesApi.reject(
            projectId,
            selectedPendingChange.id,
            reviewReason.trim() === "" ? null : reviewReason.trim(),
          );
        }

        setPendingChangeSummaries((previousSummaries) =>
          previousSummaries.filter(
            (pendingChangeSummary) =>
              pendingChangeSummary.id !== selectedPendingChange.id,
          ),
        );
        setSelectedPendingChange(null);
        await onRefreshProjectState();
        await onRefreshMessages();
      } finally {
        setReviewActionInFlight(null);
      }
    },
    [
      onRefreshMessages,
      onRefreshProjectState,
      projectId,
      reviewReason,
      selectedPendingChange,
    ],
  );

  return {
    isPendingChangesVisible,
    setIsPendingChangesVisible,
    pendingChangeSummaries,
    selectedPendingChange,
    reviewReason,
    setReviewReason,
    isPendingChangesLoading,
    reviewActionInFlight,
    approvePendingChange: async () => reviewPendingChange("approve"),
    rejectPendingChange: async () => reviewPendingChange("reject"),
  };
}
