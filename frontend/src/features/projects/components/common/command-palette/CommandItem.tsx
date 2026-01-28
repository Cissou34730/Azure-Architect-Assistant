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
        isSelected ? "bg-blue-50" : "hover:bg-gray-50"
      }`}
    >
      <div className={`mr-3 ${isSelected ? "text-blue-600" : "text-gray-400"}`}>
        {cmd.icon}
      </div>
      <span
        className={`text-sm ${
          isSelected ? "text-blue-900 font-medium" : "text-gray-900"
        }`}
      >
        {cmd.label}
      </span>
    </button>
  );
}
