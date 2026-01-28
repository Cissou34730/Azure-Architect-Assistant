import { useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { CommandPaletteContent } from "./command-palette/CommandPaletteContent";

interface CommandPaletteProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const rawParams = useParams<{ readonly projectId: string }>();
  const projectId = rawParams.projectId ?? "";

  const handleNavigate = useCallback(
    (path: string) => {
      void navigate(path);
    },
    [navigate],
  );

  if (!isOpen) return null;

  return (
    <CommandPaletteContent
      projectId={projectId}
      onNavigate={handleNavigate}
      onClose={onClose}
    />
  );
}
