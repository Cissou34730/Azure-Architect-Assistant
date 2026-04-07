import { useCallback, useEffect } from "react";
import type { SetURLSearchParams } from "react-router-dom";
import type { WorkspaceTab } from "../components/unified/workspace/types";
import {
  createProjectWorkspaceTab,
  resolveProjectWorkspaceTabIntent,
} from "../workspace.manifest";

function normalizeParam(value: string | null): string {
  if (value === null) {
    return "";
  }
  return value.trim().toLowerCase();
}

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
    openTab(createProjectWorkspaceTab("input-overview"));
  }, [openLeftPanel, openTab]);

  const handleAdrClick = useCallback(() => {
    openTab(createProjectWorkspaceTab("artifact-adrs"));
  }, [openTab]);

  return { handleUploadClick, handleAdrClick };
}

function processTabIntent(
  tabIntent: string,
  nextParams: URLSearchParams,
  { openLeftPanel, openTab }: { openLeftPanel: () => void; openTab: (tab: WorkspaceTab) => void },
): boolean {
  if (tabIntent === "") return false;
  const tab = resolveProjectWorkspaceTabIntent(tabIntent);
  if (tab === null) return false;
  if (tab.group === "input") openLeftPanel();
  openTab(tab);
  nextParams.delete("tab");
  return true;
}

function processActionIntent(
  runIntent: string,
  nextParams: URLSearchParams,
  { openTab, onGenerateCandidate }: { openTab: (tab: WorkspaceTab) => void; onGenerateCandidate: () => void },
): boolean {
  if (runIntent === "") return false;
  if (runIntent === "generate-candidate") {
    onGenerateCandidate();
  } else if (runIntent === "create-adr") {
    openTab(createProjectWorkspaceTab("artifact-adrs"));
  } else {
    return false;
  }
  nextParams.delete("action");
  nextParams.delete("prompt");
  return true;
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
    const tabUpdated = processTabIntent(
      normalizeParam(searchParams.get("tab")),
      nextParams,
      { openLeftPanel, openTab },
    );
    const runIntent = normalizeParam(searchParams.get("action")) || normalizeParam(searchParams.get("prompt"));
    const actionUpdated = processActionIntent(runIntent, nextParams, { openTab, onGenerateCandidate });
    if (tabUpdated || actionUpdated) {
      setSearchParams(nextParams, { replace: true });
    }
  }, [onGenerateCandidate, openLeftPanel, openTab, searchParams, setSearchParams]);
}
