import { useState, useEffect } from "react";
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

interface LeftContextPanelProps {
  isOpen: boolean;
  onToggle: () => void;
  requirements: readonly Requirement[];
  assumptions: readonly Assumption[];
  questions: readonly Question[];
  documents: Document[];
}

type TabType = "requirements" | "assumptions" | "questions" | "documents";

const STORAGE_KEY = "leftPanelOpen";

export function LeftContextPanel({
  isOpen,
  onToggle,
  requirements,
  assumptions,
  questions,
  documents,
}: LeftContextPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>("requirements");

  // Persist open/closed state
  useEffect(() => {
    if (isOpen !== undefined) {
      localStorage.setItem(STORAGE_KEY, String(isOpen));
    }
  }, [isOpen]);

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed left-0 top-1/2 -translate-y-1/2 bg-white border-r border-y border-gray-200 rounded-r-lg p-2 shadow-lg hover:bg-gray-50 transition-colors z-20"
        title="Show context panel"
      >
        <ChevronRight className="h-5 w-5 text-gray-600" />
      </button>
    );
  }

  const tabs = [
    { id: "requirements" as TabType, label: "Requirements", icon: FileText, count: requirements.length },
    { id: "assumptions" as TabType, label: "Assumptions", icon: Lightbulb, count: assumptions.length },
    { id: "questions" as TabType, label: "Questions", icon: HelpCircle, count: questions.length },
    { id: "documents" as TabType, label: "Documents", icon: File, count: documents.length },
  ];

  return (
    <div className="w-80 bg-gray-50 border-r border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white shrink-0">
        <h2 className="font-semibold text-gray-900">Context</h2>
        <button
          onClick={onToggle}
          className="p-1 hover:bg-gray-100 rounded transition-colors"
          title="Hide context panel"
        >
          <ChevronLeft className="h-5 w-5 text-gray-600" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 bg-white shrink-0">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex flex-col items-center gap-1 py-3 px-2 text-xs font-medium transition-colors border-b-2 ${
                isActive
                  ? "text-blue-600 border-blue-600 bg-blue-50"
                  : "text-gray-600 border-transparent hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              <div className="flex items-center gap-1">
                <Icon className="h-4 w-4" />
                {tab.count > 0 && (
                  <Badge size="sm">
                    {tab.count}
                  </Badge>
                )}
              </div>
              <span className="hidden lg:inline">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Content - Scrollable */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === "requirements" && <RequirementsTab requirements={requirements} />}
        {activeTab === "assumptions" && <AssumptionsTab assumptions={assumptions} />}
        {activeTab === "questions" && <QuestionsTab questions={questions} />}
        {activeTab === "documents" && <DocumentsTab documents={documents} />}
      </div>
    </div>
  );
}

function RequirementsTab({ requirements }: { requirements: readonly Requirement[] }) {
  const grouped = {
    business: requirements.filter((r) => r.category?.toLowerCase() === "business"),
    functional: requirements.filter((r) => r.category?.toLowerCase() === "functional"),
    nfr: requirements.filter((r) => r.category?.toLowerCase() === "nfr"),
    other: requirements.filter((r) => {
      const cat = r.category?.toLowerCase();
      return cat !== "business" && cat !== "functional" && cat !== "nfr";
    }),
  };

  if (requirements.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500">
        No requirements yet. Start chatting to identify requirements.
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {grouped.business.length > 0 && (
        <RequirementGroup title="Business" requirements={grouped.business} color="blue" />
      )}
      {grouped.functional.length > 0 && (
        <RequirementGroup title="Functional" requirements={grouped.functional} color="green" />
      )}
      {grouped.nfr.length > 0 && (
        <RequirementGroup title="Non-Functional" requirements={grouped.nfr} color="purple" />
      )}
      {grouped.other.length > 0 && (
        <RequirementGroup title="Other" requirements={grouped.other} color="gray" />
      )}
    </div>
  );
}

function RequirementGroup({
  title,
  requirements,
  color,
}: {
  title: string;
  requirements: readonly Requirement[];
  color: string;
}) {
  const colorClasses = {
    blue: "text-blue-700 bg-blue-50 border-blue-200",
    green: "text-green-700 bg-green-50 border-green-200",
    purple: "text-purple-700 bg-purple-50 border-purple-200",
    gray: "text-gray-700 bg-gray-50 border-gray-200",
  }[color];

  return (
    <div>
      <h3 className="text-xs font-semibold text-gray-900 mb-2 uppercase tracking-wide">
        {title} ({requirements.length})
      </h3>
      <div className="space-y-2">
        {requirements.map((req, idx) => (
          <div
            key={req.id || idx}
            className={`text-sm p-3 rounded-lg border ${colorClasses}`}
          >
            {req.text}
          </div>
        ))}
      </div>
    </div>
  );
}

function AssumptionsTab({ assumptions }: { assumptions: readonly Assumption[] }) {
  if (assumptions.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500">
        No assumptions documented yet.
      </div>
    );
  }

  return (
    <div className="p-4 space-y-2">
      {assumptions.map((assumption, idx) => (
        <div
          key={assumption.id || idx}
          className="flex items-start gap-2 p-3 bg-white rounded-lg border border-gray-200"
        >
          <Lightbulb className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
          <div className="text-sm text-gray-700">{assumption.text}</div>
        </div>
      ))}
    </div>
  );
}

function QuestionsTab({ questions }: { questions: readonly Question[] }) {
  if (questions.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500">
        No clarification questions at the moment.
      </div>
    );
  }

  const priorityColors = {
    1: "bg-red-100 text-red-700",
    2: "bg-amber-100 text-amber-700",
    3: "bg-blue-100 text-blue-700",
  };

  return (
    <div className="p-4 space-y-2">
      {questions.map((question, idx) => (
        <div
          key={question.id || idx}
          className="p-3 bg-white rounded-lg border border-gray-200"
        >
          <div className="flex items-start gap-2">
            <HelpCircle className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="text-sm text-gray-700 mb-2">{question.question}</div>
              <div className="flex items-center gap-2">
                {question.priority && (
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      priorityColors[question.priority as keyof typeof priorityColors] ||
                      "bg-gray-100 text-gray-700"
                    }`}
                  >
                    P{question.priority}
                  </span>
                )}
                {question.status && (
                  <span className="text-xs text-gray-500">{question.status}</span>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function DocumentsTab({ documents }: { documents: Document[] }) {
  if (documents.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500">
        No documents uploaded yet. Upload documents to provide context.
      </div>
    );
  }

  return (
    <div className="p-4 space-y-2">
      {documents.map((doc) => (
        <div
          key={doc.id}
          className="flex items-start gap-2 p-3 bg-white rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors cursor-pointer"
        >
          <File className="h-4 w-4 text-gray-600 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-gray-900 truncate">{doc.name}</div>
            {(doc.size || doc.uploadedAt) && (
              <div className="text-xs text-gray-500 mt-1">
                {doc.size && `${(doc.size / 1024).toFixed(1)} KB`}
                {doc.size && doc.uploadedAt && " • "}
                {doc.uploadedAt && new Date(doc.uploadedAt).toLocaleDateString()}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
