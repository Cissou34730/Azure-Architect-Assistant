import { useCallback, useEffect } from "react";
import type { SetURLSearchParams } from "react-router-dom";
import type { WorkspaceTab } from "../components/unified/workspace/types";
import {
  createAdrTab,
  createInputOverviewTab,
  normalizeParam,
  resolveTabIntent,
} from "./workspaceHelpers";

export function useInputDirtyIndicator({
  savedText,
  currentText,
  setDirty,
}: {
  readonly savedText: string;
  readonly currentText: string;
  readonly setDirty: (tabId: string, dirty: boolean) => void;
}) {
  useEffect(() => {
    const hasChanges = currentText.trim() !== savedText.trim();
    setDirty("input-overview", hasChanges);
  }, [currentText, savedText, setDirty]);
}

export function useWorkspaceQuickOpen(
  openLeftPanel: () => void,
  openTab: (tab: WorkspaceTab) => void,
) {
  const handleUploadClick = useCallback(() => {
    openLeftPanel();
    openTab(createInputOverviewTab());
  }, [openLeftPanel, openTab]);

  const handleAdrClick = useCallback(() => {
    openTab({
      id: "artifact-adrs",
      kind: "artifact-adrs",
      title: "ADRs",
      group: "artifact",
      pinned: false,
      dirty: false,
    });
  }, [openTab]);

  return { handleUploadClick, handleAdrClick };
}

export function useRouteIntentHandlers({
  searchParams,
  setSearchParams,
  openLeftPanel,
  openTab,
  onGenerateCandidate,
}: {
  readonly searchParams: URLSearchParams;
  readonly setSearchParams: SetURLSearchParams;
  readonly openLeftPanel: () => void;
  readonly openTab: (tab: WorkspaceTab) => void;
  readonly onGenerateCandidate: () => void;
}) {
  useEffect(() => {
    const nextParams = new URLSearchParams(searchParams);
    let shouldUpdateUrl = false;

    const tabIntent = normalizeParam(searchParams.get("tab"));
    if (tabIntent !== "") {
      const tab = resolveTabIntent(tabIntent);
      if (tab !== null) {
        if (tab.group === "input") {
          openLeftPanel();
        }
        openTab(tab);
        nextParams.delete("tab");
        shouldUpdateUrl = true;
      }
    }

    const actionIntent = normalizeParam(searchParams.get("action"));
    const promptIntent = normalizeParam(searchParams.get("prompt"));
    const runIntent = actionIntent !== "" ? actionIntent : promptIntent;
    let consumedAction = false;
    if (runIntent !== "") {
      if (runIntent === "generate-candidate") {
        onGenerateCandidate();
        consumedAction = true;
        shouldUpdateUrl = true;
      } else if (runIntent === "create-adr") {
        openTab(createAdrTab());
        consumedAction = true;
        shouldUpdateUrl = true;
      }
      if (consumedAction) {
        nextParams.delete("action");
        nextParams.delete("prompt");
      }
    }

    if (shouldUpdateUrl) {
      setSearchParams(nextParams, { replace: true });
    }
  }, [
    onGenerateCandidate,
    openLeftPanel,
    openTab,
    searchParams,
    setSearchParams,
  ]);
}
