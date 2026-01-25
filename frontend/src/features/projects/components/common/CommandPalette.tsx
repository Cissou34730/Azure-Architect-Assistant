import React, { useState, useEffect, useMemo } from "react";
import { Search, X, FileText, MessageSquare, BarChart2, Upload, Download, HelpCircle } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

interface Command {
  id: string;
  label: string;
  icon: React.ReactNode;
  keywords: string[];
  action: () => void;
  category: "Navigation" | "Actions" | "Help";
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose }) => {
  const [search, setSearch] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const navigate = useNavigate();
  const { projectId } = useParams();

  const commands: Command[] = useMemo(
    () => [
      // Navigation
      {
        id: "nav-overview",
        label: "Go to Overview",
        icon: <BarChart2 className="h-4 w-4" />,
        keywords: ["overview", "dashboard", "home", "stats"],
        action: () => navigate(`/projects/${projectId}/overview`),
        category: "Navigation",
      },
      {
        id: "nav-workspace",
        label: "Go to Workspace",
        icon: <MessageSquare className="h-4 w-4" />,
        keywords: ["workspace", "chat", "assistant", "talk"],
        action: () => navigate(`/projects/${projectId}/workspace`),
        category: "Navigation",
      },
      {
        id: "nav-deliverables",
        label: "Go to Deliverables",
        icon: <FileText className="h-4 w-4" />,
        keywords: ["deliverables", "diagrams", "adr", "iac", "costs"],
        action: () => navigate(`/projects/${projectId}/deliverables`),
        category: "Navigation",
      },
      {
        id: "nav-diagrams",
        label: "View Diagrams",
        icon: <FileText className="h-4 w-4" />,
        keywords: ["diagrams", "architecture", "c4", "visual"],
        action: () => navigate(`/projects/${projectId}/deliverables?tab=diagrams`),
        category: "Navigation",
      },
      {
        id: "nav-adrs",
        label: "View ADRs",
        icon: <FileText className="h-4 w-4" />,
        keywords: ["adr", "decisions", "architecture decision records"],
        action: () => navigate(`/projects/${projectId}/deliverables?tab=adrs`),
        category: "Navigation",
      },
      {
        id: "nav-iac",
        label: "View IaC",
        icon: <FileText className="h-4 w-4" />,
        keywords: ["iac", "infrastructure", "bicep", "terraform", "code"],
        action: () => navigate(`/projects/${projectId}/deliverables?tab=iac`),
        category: "Navigation",
      },
      {
        id: "nav-costs",
        label: "View Cost Estimates",
        icon: <BarChart2 className="h-4 w-4" />,
        keywords: ["cost", "pricing", "estimate", "budget", "money"],
        action: () => navigate(`/projects/${projectId}/deliverables?tab=costs`),
        category: "Navigation",
      },
      // Actions
      {
        id: "action-upload",
        label: "Upload Documents",
        icon: <Upload className="h-4 w-4" />,
        keywords: ["upload", "documents", "files", "add"],
        action: () => {
          navigate(`/projects/${projectId}/workspace`);
          // Focus document upload area after navigation
          setTimeout(() => {
            const uploadArea = document.querySelector('[data-upload-area]');
            if (uploadArea) uploadArea.scrollIntoView({ behavior: "smooth" });
          }, 100);
        },
        category: "Actions",
      },
      {
        id: "action-export-adrs",
        label: "Export All ADRs",
        icon: <Download className="h-4 w-4" />,
        keywords: ["export", "download", "adr", "save"],
        action: () => {
          navigate(`/projects/${projectId}/deliverables?tab=adrs`);
          // Trigger export after navigation
          setTimeout(() => {
            const exportBtn = document.querySelector('[data-export-adrs]') as HTMLButtonElement;
            if (exportBtn) exportBtn.click();
          }, 100);
        },
        category: "Actions",
      },
      {
        id: "action-export-iac",
        label: "Download IaC Files",
        icon: <Download className="h-4 w-4" />,
        keywords: ["download", "iac", "infrastructure", "code", "bicep", "terraform"],
        action: () => {
          navigate(`/projects/${projectId}/deliverables?tab=iac`);
          setTimeout(() => {
            const downloadBtn = document.querySelector('[data-download-all-iac]') as HTMLButtonElement;
            if (downloadBtn) downloadBtn.click();
          }, 100);
        },
        category: "Actions",
      },
      // Help
      {
        id: "help-shortcuts",
        label: "View Keyboard Shortcuts",
        icon: <HelpCircle className="h-4 w-4" />,
        keywords: ["help", "shortcuts", "keyboard", "keys", "hotkeys"],
        action: () => {
          alert(
            "Keyboard Shortcuts:\n\n" +
              "Cmd/Ctrl + K: Open Command Palette\n" +
              "Cmd/Ctrl + /: Toggle Context Sidebar\n" +
              "Cmd/Ctrl + Enter: Send Chat Message\n" +
              "Esc: Close Modals/Palette"
          );
        },
        category: "Help",
      },
    ],
    [navigate, projectId]
  );

  const filteredCommands = useMemo(() => {
    if (!search.trim()) return commands;

    const searchLower = search.toLowerCase();
    return commands.filter(
      (cmd) =>
        cmd.label.toLowerCase().includes(searchLower) ||
        cmd.keywords.some((kw) => kw.toLowerCase().includes(searchLower))
    );
  }, [commands, search]);

  const groupedCommands = useMemo(() => {
    const groups: Record<string, Command[]> = {};
    filteredCommands.forEach((cmd) => {
      if (!groups[cmd.category]) groups[cmd.category] = [];
      groups[cmd.category].push(cmd);
    });
    return groups;
  }, [filteredCommands]);

  useEffect(() => {
    if (!isOpen) {
      setSearch("");
      setSelectedIndex(0);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % filteredCommands.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + filteredCommands.length) % filteredCommands.length);
      } else if (e.key === "Enter") {
        e.preventDefault();
        const cmd = filteredCommands[selectedIndex];
        if (cmd) {
          cmd.action();
          onClose();
        }
      } else if (e.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, selectedIndex, filteredCommands, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-start justify-center pt-[20vh]">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-2xl overflow-hidden">
        {/* Search Input */}
        <div className="flex items-center px-4 py-3 border-b border-gray-200">
          <Search className="h-5 w-5 text-gray-400 mr-3" />
          <input
            type="text"
            placeholder="Type a command or search..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setSelectedIndex(0);
            }}
            autoFocus
            className="flex-1 outline-none text-gray-900 placeholder-gray-400"
          />
          <button
            onClick={onClose}
            aria-label="Close command palette"
            className="ml-2 p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        {/* Command List */}
        <div className="max-h-96 overflow-y-auto">
          {filteredCommands.length === 0 ? (
            <div className="py-12 text-center text-gray-500">
              <p>No commands found</p>
              <p className="text-sm mt-1">Try a different search term</p>
            </div>
          ) : (
            Object.entries(groupedCommands).map(([category, cmds]) => (
              <div key={category}>
                <div className="px-4 py-2 text-xs font-semibold text-gray-500 bg-gray-50">
                  {category}
                </div>
                {cmds.map((cmd) => {
                  const globalIndex = filteredCommands.indexOf(cmd);
                  const isSelected = globalIndex === selectedIndex;

                  return (
                    <button
                      key={cmd.id}
                      onClick={() => {
                        cmd.action();
                        onClose();
                      }}
                      onMouseEnter={() => setSelectedIndex(globalIndex)}
                      className={`w-full flex items-center px-4 py-3 text-left transition-colors ${
                        isSelected ? "bg-blue-50" : "hover:bg-gray-50"
                      }`}
                    >
                      <div
                        className={`mr-3 ${
                          isSelected ? "text-blue-600" : "text-gray-400"
                        }`}
                      >
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
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-gray-200 bg-gray-50 flex items-center justify-between text-xs text-gray-500">
          <div className="flex gap-4">
            <span>
              <kbd className="px-2 py-1 bg-white border border-gray-300 rounded text-xs">↑↓</kbd> Navigate
            </span>
            <span>
              <kbd className="px-2 py-1 bg-white border border-gray-300 rounded text-xs">Enter</kbd> Select
            </span>
          </div>
          <span>
            <kbd className="px-2 py-1 bg-white border border-gray-300 rounded text-xs">Esc</kbd> Close
          </span>
        </div>
      </div>
    </div>
  );
};
