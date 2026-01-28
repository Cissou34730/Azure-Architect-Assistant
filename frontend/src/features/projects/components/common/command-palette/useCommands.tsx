import { useMemo } from "react";
import type { Command } from "./types";
import { getCommands } from "./getCommands";

interface UseCommandsProps {
  readonly projectId: string;
  readonly onNavigate: (path: string) => void;
  readonly search: string;
}

export function useCommands({ projectId, onNavigate, search }: UseCommandsProps) {
  const commands = useMemo((): readonly Command[] => {
    return getCommands({ projectId, onNavigate });
  }, [projectId, onNavigate]);

  const filteredCommands = useMemo(() => {
    const trimmed = search.trim();
    if (trimmed === "") return commands;

    const searchLower = trimmed.toLowerCase();
    return commands.filter(
      (cmd) =>
        cmd.label.toLowerCase().includes(searchLower) ||
        cmd.keywords.some((kw) => kw.toLowerCase().includes(searchLower)),
    );
  }, [commands, search]);

  const groupedCommands = useMemo(() => {
    const groups: Record<string, Command[]> = {};
    for (const cmd of filteredCommands) {
      groups[cmd.category] ??= [];
      groups[cmd.category].push(cmd);
    }
    return groups;
  }, [filteredCommands]);

  return { filteredCommands, groupedCommands };
}
