import type { Command } from "./types";

interface CommandItemProps {
  readonly cmd: Command;
  readonly isSelected: boolean;
  readonly onSelect: () => void;
  readonly onAction: () => void;
}

export function CommandItem({
  cmd,
  isSelected,
  onSelect,
  onAction,
}: CommandItemProps) {
  return (
    <button
      type="button"
      onClick={onAction}
      onMouseEnter={onSelect}
      className={`w-full flex items-center px-4 py-3 text-left transition-colors ${
        isSelected ? "bg-brand-soft" : "hover:bg-surface"
      }`}
    >
      <div className={`mr-3 ${isSelected ? "text-brand" : "text-dim"}`}>
        {cmd.icon}
      </div>
      <span
        className={`text-sm ${
          isSelected ? "text-brand-strong font-medium" : "text-foreground"
        }`}
      >
        {cmd.label}
      </span>
    </button>
  );
}


