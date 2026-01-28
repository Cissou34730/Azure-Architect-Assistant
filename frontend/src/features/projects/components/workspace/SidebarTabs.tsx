import {
  FileText,
  HelpCircle,
  Lightbulb,
  ListChecks,
  LucideIcon,
} from "lucide-react";
import { Badge } from "../../../../components/common";

export type TabType = "requirements" | "assumptions" | "questions" | "documents";

export interface SidebarTabConfig {
  id: TabType;
  label: string;
  icon: LucideIcon;
}

// eslint-disable-next-line react-refresh/only-export-components -- Shared config constant
export const SIDEBAR_TABS_CONFIG: SidebarTabConfig[] = [
  { id: "requirements", label: "Requirements", icon: ListChecks },
  { id: "assumptions", label: "Assumptions", icon: Lightbulb },
  { id: "questions", label: "Questions", icon: HelpCircle },
  { id: "documents", label: "Documents", icon: FileText },
];

export interface Requirement {
  readonly id?: string;
  readonly category?: string;
  readonly text?: string;
}

export interface Assumption {
  readonly id?: string;
  readonly text?: string;
}

export interface Question {
  readonly id?: string;
  readonly question?: string;
  readonly priority?: number;
  readonly status?: string;
}

export interface Document {
  id: string;
  name: string;
  size?: number;
  uploadedAt?: string;
}

export function RequirementsTab({
  requirements,
}: {
  requirements: readonly Requirement[];
}) {
  const grouped: Record<string, Requirement[]> = {
    business: [],
    functional: [],
    nfr: [],
    other: [],
  };

  for (const req of requirements) {
    const cat = (req.category ?? "Other").toLowerCase();
    if (cat === "business") {
      grouped.business.push(req);
    } else if (cat === "functional") {
      grouped.functional.push(req);
    } else if (cat === "nfr") {
      grouped.nfr.push(req);
    } else {
      grouped.other.push(req);
    }
  }

  if (requirements.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 text-sm">
        No requirements yet
      </div>
    );
  }

  const categoryLabels: Record<string, string> = {
    business: "Business",
    functional: "Functional",
    nfr: "NFR",
    other: "Other",
  };

  return (
    <div className="p-4 space-y-4">
      {Object.entries(grouped).map(([category, items]) => {
        if (items.length === 0) {
          return null;
        }

        return (
          <div key={category}>
            <h4 className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-2">
              {categoryLabels[category]}
              <Badge variant="default" size="sm">
                {items.length}
              </Badge>
            </h4>
            <div className="space-y-2">
              {items.map((req, idx) => (
                <div
                  key={req.id ?? `req-${idx}`}
                  className="bg-gray-50 rounded p-2 text-xs text-gray-800"
                >
                  {req.text ?? "Untitled"}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function AssumptionsTab({
  assumptions,
}: {
  assumptions: readonly Assumption[];
}) {
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
          key={assumption.id ?? `asm-${idx}`}
          className="bg-amber-50 border border-amber-200 rounded p-3 text-xs text-gray-800"
        >
          <div className="flex items-start gap-2">
            <Lightbulb className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
            <p>{assumption.text ?? "Untitled assumption"}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

export function QuestionsTab({ questions }: { questions: readonly Question[] }) {
  if (questions.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 text-sm">
        No clarification questions yet
      </div>
    );
  }

  const sorted = [...questions].sort(
    (a, b) => (a.priority ?? 999) - (b.priority ?? 999),
  );

  return (
    <div className="p-4 space-y-2">
      {sorted.map((q, idx) => {
        const rawStatus = q.status ?? "open";
        const status = rawStatus.toLowerCase();
        const isOpen = status === "open" || status === "pending";

        return (
          <div
            key={q.id ?? `q-${idx}`}
            className={`border rounded p-3 text-xs ${
              isOpen ? "bg-blue-50 border-blue-200" : "bg-gray-50 border-gray-200"
            }`}
          >
            <div className="flex items-start justify-between gap-2 mb-1">
              <Badge variant={isOpen ? "primary" : "default"} size="sm">
                P{q.priority ?? "-"}
              </Badge>
              <Badge variant={isOpen ? "warning" : "success"} size="sm">
                {status}
              </Badge>
            </div>
            <p className="text-gray-800">{q.question ?? "Untitled question"}</p>
          </div>
        );
      })}
    </div>
  );
}

function formatFileSize(bytes?: number) {
  if (bytes === undefined) {
    return "—";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentsTab({ documents }: { documents: Document[] }) {
  if (documents.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 text-sm">
        No documents uploaded yet
      </div>
    );
  }

  return (
    <div className="p-4 space-y-2">
      {documents.map((doc) => (
        <div
          key={doc.id}
          className="bg-gray-50 border border-gray-200 rounded p-3"
        >
          <div className="flex items-start gap-2">
            <FileText className="h-4 w-4 text-gray-600 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-900 truncate">
                {doc.name}
              </p>
              <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                {doc.size !== undefined && (
                  <span>{formatFileSize(doc.size)}</span>
                )}
                {doc.uploadedAt !== undefined && (
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
