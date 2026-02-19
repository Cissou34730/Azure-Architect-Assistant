import { useEffect, useState, RefObject } from "react";
import { ProjectSelectorDropdownRef } from "../../../components/common/ProjectSelectorDropdown";
import { KeyboardShortcut } from "./ProjectHeaderShortcuts";

interface UseProjectHeaderKeyboardProps {
  onUploadClick?: () => void;
  projectSelectorRef: RefObject<ProjectSelectorDropdownRef | null>;
}

export function useProjectHeaderKeyboard({
  onUploadClick,
  projectSelectorRef,
}: UseProjectHeaderKeyboardProps) {
  const [showShortcuts, setShowShortcuts] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isCmdOrCtrl = e.metaKey || e.ctrlKey;
      if (!isCmdOrCtrl) return;
      const key = e.key.toLowerCase();
      if (key === "p") {
        e.preventDefault();
        projectSelectorRef.current?.toggle();
      }
      if (key === "k") {
        e.preventDefault();
        setShowShortcuts((prev) => !prev);
      }
      if (key === "u" && onUploadClick !== undefined) {
        e.preventDefault();
        onUploadClick();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onUploadClick, projectSelectorRef]);

  const shortcuts: KeyboardShortcut[] = getShortcuts({
    onUploadClick,
    projectSelectorRef,
    setShowShortcuts,
  });

  return { showShortcuts, setShowShortcuts, shortcuts };
}

interface GetShortcutsProps extends UseProjectHeaderKeyboardProps {
  setShowShortcuts: (value: React.SetStateAction<boolean>) => void;
}

function getShortcuts({
  onUploadClick,
  projectSelectorRef,
  setShowShortcuts,
}: GetShortcutsProps): KeyboardShortcut[] {
  return [
    {
      key: "⌘P",
      label: "Switch Project",
      action: () => {
        projectSelectorRef.current?.open();
      },
    },
    {
      key: "⌘U",
      label: "Open Inputs Setup",
      action: () => {
        onUploadClick?.();
      },
      visible: onUploadClick !== undefined,
    },
    {
      key: "⌘K",
      label: "Shortcuts",
      action: () => {
        setShowShortcuts((p) => !p);
      },
    },
  ].filter((s) => s.visible !== false);
}
