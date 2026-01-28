import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Badge } from "../../../../components/common";
import {
  RequirementsTab,
  AssumptionsTab,
  QuestionsTab,
  DocumentsTab,
  SIDEBAR_TABS_CONFIG,
  type Requirement,
  type Assumption,
  type Question,
  type Document,
  type TabType,
} from "./SidebarTabs";

interface ContextSidebarProps {
  requirements: readonly Requirement[];
  assumptions: readonly Assumption[];
  questions: readonly Question[];
  documents: Document[];
  isOpen: boolean;
  onToggle: () => void;
}

export function ContextSidebar({
  requirements,
  assumptions,
  questions,
  documents,
  isOpen,
  onToggle,
}: ContextSidebarProps) {
  const [activeTab, setActiveTab] = useState<TabType>("requirements");

  const getTabCount = (tabId: TabType): number => {
    switch (tabId) {
      case "requirements":
        return requirements.length;
      case "assumptions":
        return assumptions.length;
      case "questions":
        return questions.length;
      case "documents":
        return documents.length;
      default:
        return 0;
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed right-0 top-1/2 -translate-y-1/2 bg-white border border-gray-200 rounded-l-lg p-2 shadow-md hover:bg-gray-50 transition-colors z-10"
        aria-label="Open context sidebar"
      >
        <ChevronLeft className="h-5 w-5 text-gray-600" />
      </button>
    );
  }

  return (
    <div className="h-full flex flex-col border-l border-gray-200 bg-white">
      {/* Header with close button */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Context</h3>
        <button
          onClick={onToggle}
          className="p-1 hover:bg-gray-100 rounded transition-colors"
          aria-label="Close sidebar"
        >
          <ChevronRight className="h-5 w-5 text-gray-600" />
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 flex">
        {SIDEBAR_TABS_CONFIG.map((tab) => {
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
              }}
              className={`flex-1 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                isActive
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              <tab.icon className="h-4 w-4 mx-auto mb-1" />
              <div className="flex items-center justify-center gap-1">
                <span className="hidden sm:inline">{tab.label}</span>
                <Badge variant="default" size="sm">
                  {getTabCount(tab.id)}
                </Badge>
              </div>
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === "requirements" && (
          <RequirementsTab requirements={requirements} />
        )}
        {activeTab === "assumptions" && (
          <AssumptionsTab assumptions={assumptions} />
        )}
        {activeTab === "questions" && (
          <QuestionsTab questions={questions} />
        )}
        {activeTab === "documents" && (
          <DocumentsTab documents={documents} />
        )}
      </div>
    </div>
  );
}
