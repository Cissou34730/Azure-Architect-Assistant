import { useState } from "react";
import { ChevronLeft, ChevronRight, FileText, HelpCircle, Lightbulb, File } from "lucide-react";
import { Badge } from "../../../../components/common";

interface Requirement {
  readonly id?: string;
  readonly category?: string;
  readonly text?: string;
}

interface Assumption {
  readonly id?: string;
  readonly text?: string;
}

interface Question {
  readonly id?: string;
  readonly question?: string;
  readonly priority?: number;
  readonly status?: string;
}

interface Document {
  id: string;
  name: string;
  size?: number;
  uploadedAt?: string;
}

interface ContextSidebarProps {
  requirements: readonly Requirement[];
  assumptions: readonly Assumption[];
  questions: readonly Question[];
  documents: Document[];
  isOpen: boolean;
  onToggle: () => void;
}

type TabType = "requirements" | "assumptions" | "questions" | "documents";

export function ContextSidebar({
  requirements,
  assumptions,
  questions,
  documents,
  isOpen,
  onToggle,
}: ContextSidebarProps) {
  const [activeTab, setActiveTab] = useState<TabType>("requirements");

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

  const tabs: { id: TabType; label: string; icon: typeof FileText; count: number }[] = [
    { id: "requirements", label: "Requirements", icon: FileText, count: requirements.length },
    { id: "assumptions", label: "Assumptions", icon: Lightbulb, count: assumptions.length },
    { id: "questions", label: "Questions", icon: HelpCircle, count: questions.length },
    { id: "documents", label: "Documents", icon: File, count: documents.length },
  ];

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
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                isActive
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              <Icon className="h-4 w-4 mx-auto mb-1" />
              <div className="flex items-center justify-center gap-1">
                <span className="hidden sm:inline">{tab.label}</span>
                <Badge variant="default" size="sm">
                  {tab.count}
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

function RequirementsTab({ requirements }: { requirements: readonly Requirement[] }) {
  const grouped: Record<string, Requirement[]> = {
    Business: [],
    Functional: [],
    NFR: [],
    Other: [],
  };

  for (const req of requirements) {
    const cat = req.category || "Other";
    if (cat.toLowerCase() === "business") grouped.Business.push(req);
    else if (cat.toLowerCase() === "functional") grouped.Functional.push(req);
    else if (cat.toLowerCase() === "nfr") grouped.NFR.push(req);
    else grouped.Other.push(req);
  }

  if (requirements.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 text-sm">
        No requirements yet
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {Object.entries(grouped).map(([category, items]) => {
        if (items.length === 0) return null;

        return (
          <div key={category}>
            <h4 className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-2">
              {category}
              <Badge variant="default" size="sm">{items.length}</Badge>
            </h4>
            <div className="space-y-2">
              {items.map((req, idx) => (
                <div
                  key={req.id || idx}
                  className="bg-gray-50 rounded p-2 text-xs text-gray-800"
                >
                  {req.text || "Untitled"}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function AssumptionsTab({ assumptions }: { assumptions: readonly Assumption[] }) {
  if (assumptions.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 text-sm">
        No assumptions yet
      </div>
    );
  }

  return (
    <div className="p-4 space-y-2">
      {assumptions.map((assumption, idx) => (
        <div
          key={assumption.id || idx}
          className="bg-amber-50 border border-amber-200 rounded p-3 text-xs text-gray-800"
        >
          <div className="flex items-start gap-2">
            <Lightbulb className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
            <p>{assumption.text || "Untitled assumption"}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function QuestionsTab({ questions }: { questions: readonly Question[] }) {
  if (questions.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 text-sm">
        No clarification questions yet
      </div>
    );
  }

  const sorted = [...questions].sort((a, b) => (a.priority || 999) - (b.priority || 999));

  return (
    <div className="p-4 space-y-2">
      {sorted.map((q, idx) => {
        const status = (q.status || "open").toLowerCase();
        const isOpen = status === "open" || status === "pending";

        return (
          <div
            key={q.id || idx}
            className={`border rounded p-3 text-xs ${
              isOpen
                ? "bg-blue-50 border-blue-200"
                : "bg-gray-50 border-gray-200"
            }`}
          >
            <div className="flex items-start justify-between gap-2 mb-1">
              <Badge variant={isOpen ? "primary" : "default"} size="sm">
                P{q.priority || "-"}
              </Badge>
              <Badge variant={isOpen ? "warning" : "success"} size="sm">
                {status}
              </Badge>
            </div>
            <p className="text-gray-800">{q.question || "Untitled question"}</p>
          </div>
        );
      })}
    </div>
  );
}

function DocumentsTab({ documents }: { documents: Document[] }) {
  if (documents.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 text-sm">
        No documents uploaded yet
      </div>
    );
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return "—";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="p-4 space-y-2">
      {documents.map((doc) => (
        <div
          key={doc.id}
          className="bg-gray-50 border border-gray-200 rounded p-3"
        >
          <div className="flex items-start gap-2">
            <File className="h-4 w-4 text-gray-600 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-900 truncate">
                {doc.name}
              </p>
              <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                {doc.size && <span>{formatFileSize(doc.size)}</span>}
                {doc.uploadedAt && (
                  <>
                    <span>•</span>
                    <span>{new Date(doc.uploadedAt).toLocaleDateString()}</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
