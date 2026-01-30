import { Search, X } from "lucide-react";

interface PaletteInputProps {
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly onClose: () => void;
}

export function PaletteInput({ value, onChange, onClose }: PaletteInputProps) {
  return (
    <div className="flex items-center px-4 py-3 border-b border-gray-200">
      <Search className="h-5 w-5 text-gray-400 mr-3" />
      <input
        type="text"
        placeholder="Type a command or search..."
        value={value}
        onChange={(event) => {
          onChange(event.target.value);
        }}
        autoFocus
        className="flex-1 outline-none text-gray-900 placeholder-gray-400"
      />
      <button
        type="button"
        onClick={onClose}
        aria-label="Close command palette"
        className="ml-2 p-1 hover:bg-gray-100 rounded transition-colors"
      >
        <X className="h-5 w-5 text-gray-500" />
      </button>
    </div>
  );
}
