import {
  FolderOpen,
  FileText,
  MessageSquare,
  BarChart2,
  Download,
  HelpCircle,
} from "lucide-react";
import type { Command } from "./types";

interface GetCommandsProps {
  readonly projectId: string;
  readonly onNavigate: (path: string) => void;
}

function getNavigationCommands(
  projectId: string,
  onNavigate: (path: string) => void,
): readonly Command[] {
  return [
    {
      id: "nav-overview",
      label: "Go to Overview",
      icon: <BarChart2 className="h-4 w-4" />,
      keywords: ["overview", "dashboard", "home", "stats"],
      action: () => {
        onNavigate(`/project/${projectId}`);
      },
      category: "Navigation",
    },
    {
      id: "nav-workspace",
      label: "Go to Workspace",
      icon: <MessageSquare className="h-4 w-4" />,
      keywords: ["workspace", "chat", "assistant", "talk"],
      action: () => {
        onNavigate(`/project/${projectId}`);
      },
      category: "Navigation",
    },
    {
      id: "nav-deliverables",
      label: "Go to Deliverables",
      icon: <FileText className="h-4 w-4" />,
      keywords: ["deliverables", "diagrams", "adr", "iac", "costs"],
      action: () => {
        onNavigate(`/project/${projectId}?tab=deliverables`);
      },
      category: "Navigation",
    },
    {
      id: "nav-diagrams",
      label: "View Diagrams",
      icon: <FileText className="h-4 w-4" />,
      keywords: ["diagrams", "architecture", "c4", "visual"],
      action: () => {
        onNavigate(`/project/${projectId}?tab=diagrams`);
      },
      category: "Navigation",
    },
    {
      id: "nav-adrs",
      label: "View ADRs",
      icon: <FileText className="h-4 w-4" />,
      keywords: ["adr", "decisions", "architecture decision records"],
      action: () => {
        onNavigate(`/project/${projectId}?tab=adrs`);
      },
      category: "Navigation",
    },
    {
      id: "nav-iac",
      label: "View IaC",
      icon: <FileText className="h-4 w-4" />,
      keywords: ["iac", "infrastructure", "bicep", "terraform", "code"],
      action: () => {
        onNavigate(`/project/${projectId}?tab=iac`);
      },
      category: "Navigation",
    },
    {
      id: "nav-costs",
      label: "View Cost Estimates",
      icon: <BarChart2 className="h-4 w-4" />,
      keywords: ["cost", "pricing", "estimate", "budget", "money"],
      action: () => {
        onNavigate(`/project/${projectId}?tab=costs`);
      },
      category: "Navigation",
    },
  ];
}

function getActionCommands(
  projectId: string,
  onNavigate: (path: string) => void,
): readonly Command[] {
  return [
    {
      id: "action-upload",
      label: "Open Inputs Setup",
      icon: <FolderOpen className="h-4 w-4" />,
      keywords: ["upload", "documents", "files", "inputs", "setup"],
      action: () => {
        onNavigate(`/project/${projectId}?tab=inputs`);
      },
      category: "Actions",
    },
    {
      id: "action-export-adrs",
      label: "Export All ADRs",
      icon: <Download className="h-4 w-4" />,
      keywords: ["export", "download", "adr", "save"],
      action: () => {
        onNavigate(`/project/${projectId}?tab=adrs`);
        setTimeout(() => {
          const exportBtn = document.querySelector("[data-export-adrs]");
          if (exportBtn instanceof HTMLElement) {
            exportBtn.click();
          }
        }, 100);
      },
      category: "Actions",
    },
    {
      id: "action-export-iac",
      label: "Download IaC Files",
      icon: <Download className="h-4 w-4" />,
      keywords: [
        "download",
        "iac",
        "infrastructure",
        "code",
        "bicep",
        "terraform",
      ],
      action: () => {
        onNavigate(`/project/${projectId}?tab=iac`);
        setTimeout(() => {
          const downloadBtn = document.querySelector("[data-download-all-iac]");
          if (downloadBtn instanceof HTMLElement) {
            downloadBtn.click();
          }
        }, 100);
      },
      category: "Actions",
    },
  ];
}

function getHelpCommands(): readonly Command[] {
  return [
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
            "Esc: Close Modals/Palette",
        );
      },
      category: "Help",
    },
  ];
}

export function getCommands({
  projectId,
  onNavigate,
}: GetCommandsProps): readonly Command[] {
  return [
    ...getNavigationCommands(projectId, onNavigate),
    ...getActionCommands(projectId, onNavigate),
    ...getHelpCommands(),
  ];
}
