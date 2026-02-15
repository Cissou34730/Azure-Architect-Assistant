import { useState, useEffect } from "react";
import { useCommands } from "./useCommands";
import { PaletteInput } from "./PaletteInput";
import { PaletteList } from "./PaletteList";
import { PaletteFooter } from "./PaletteFooter";

interface CommandPaletteContentProps {
  readonly projectId: string;
  readonly onNavigate: (path: string) => void;
  readonly onClose: () => void;
}

export function CommandPaletteContent({
  projectId,
  onNavigate,
  onClose,
}: CommandPaletteContentProps) {
  const [search, setSearch] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  const { filteredCommands, groupedCommands } = useCommands({
    projectId,
    onNavigate,
    search,
  });

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setSelectedIndex((prev) =>
          filteredCommands.length > 0 ? (prev + 1) % filteredCommands.length : 0,
        );
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        setSelectedIndex((prev) =>
          filteredCommands.length > 0
            ? (prev - 1 + filteredCommands.length) % filteredCommands.length
            : 0,
        );
      } else if (event.key === "Enter") {
        event.preventDefault();
        const cmd = filteredCommands[selectedIndex];
        cmd.action();
        onClose();
      } else if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [selectedIndex, filteredCommands, onClose]);

  return (
    <div className="fixed inset-0 bg-overlay/50 z-50 flex items-start justify-center pt-[20vh]">
      <div className="bg-card rounded-lg shadow-2xl w-full max-w-2xl overflow-hidden">
        <PaletteInput
          value={search}
          onChange={(val) => {
            setSearch(val);
            setSelectedIndex(0);
          }}
          onClose={onClose}
        />

        <PaletteList
          filteredCommands={filteredCommands}
          groupedCommands={groupedCommands}
          selectedIndex={selectedIndex}
          onSelect={setSelectedIndex}
          onAction={(cmd) => {
            cmd.action();
            onClose();
          }}
        />

        <PaletteFooter />
      </div>
    </div>
  );
}


