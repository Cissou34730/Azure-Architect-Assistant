import { CommandItem } from "./CommandItem";
import type { Command } from "./types";

interface PaletteListProps {
  readonly filteredCommands: readonly Command[];
  readonly groupedCommands: Record<string, Command[]>;
  readonly selectedIndex: number;
  readonly onSelect: (index: number) => void;
  readonly onAction: (cmd: Command) => void;
}

export function PaletteList({
  filteredCommands,
  groupedCommands,
  selectedIndex,
  onSelect,
  onAction,
}: PaletteListProps) {
  if (filteredCommands.length === 0) {
    return (
      <div className="py-12 text-center text-dim">
        <p>No commands found</p>
        <p className="text-sm mt-1">Try a different search term</p>
      </div>
    );
  }

  return (
    <div className="max-h-96 overflow-y-auto">
      {Object.entries(groupedCommands).map(([category, cmds]) => (
        <div key={category}>
          <div className="px-4 py-2 text-xs font-semibold text-dim bg-surface">
            {category}
          </div>
          {cmds.map((cmd) => {
            const globalIndex = filteredCommands.indexOf(cmd);
            const isSelected = globalIndex === selectedIndex;

            return (
              <CommandItem
                key={cmd.id}
                cmd={cmd}
                isSelected={isSelected}
                onSelect={() => {
                  onSelect(globalIndex);
                }}
                onAction={() => {
                  onAction(cmd);
                }}
              />
            );
          })}
        </div>
      ))}
    </div>
  );
}

