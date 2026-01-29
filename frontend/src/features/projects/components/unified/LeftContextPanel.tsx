import { useState, useEffect, useMemo, memo } from "react";
import { ChevronLeft, ChevronRight, FileText, HelpCircle, Lightbulb, File } from "lucide-react";
import { useProjectStateContext } from "../../context/useProjectStateContext";
import { TabHeader } from "./LeftContextPanel/TabHeader";
import { TabContent } from "./LeftContextPanel/TabContent";
import type { TabType, TabItem } from "./LeftContextPanel/TabHeader";
import { useRenderCount } from "../../../../hooks/useRenderCount";

interface LeftContextPanelProps {
  readonly isOpen: boolean;
  readonly onToggle: () => void;
}

const STORAGE_KEY = "leftPanelOpen";

function LeftContextPanelBase({ isOpen, onToggle }: LeftContextPanelProps) {
  useRenderCount("LeftContextPanel");
  const [activeTab, setActiveTab] = useState<TabType>("requirements");
  const { projectState } = useProjectStateContext();

  const requirements = useMemo(() => projectState?.requirements ?? [], [projectState?.requirements]);
  const assumptions = useMemo(() => projectState?.assumptions ?? [], [projectState?.assumptions]);
  const questions = useMemo(() => projectState?.clarificationQuestions ?? [], [projectState?.clarificationQuestions]);
  const documents = useMemo(() => projectState?.referenceDocuments ?? [], [projectState?.referenceDocuments]);

  // Task 4.1: Memoize requirements filtering in the panel
  const functionalReqs = useMemo(() =>
    requirements.filter(r => (r.category ?? "").toLowerCase() === "functional"),
    [requirements]
  );

  const nfrReqs = useMemo(() =>
    requirements.filter(r => (r.category ?? "").toLowerCase() === "nfr" || (r.category ?? "").toLowerCase() === "non-functional"),
    [requirements]
  );

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(isOpen));
  }, [isOpen]);

  const tabs: readonly TabItem[] = useMemo(
    () => [
      { 
        id: "requirements", 
        label: "Requirements", 
        icon: FileText, 
        count: requirements.length,
        tooltip: `${functionalReqs.length} Functional, ${nfrReqs.length} NFR`
      },
      { id: "assumptions", label: "Assumptions", icon: Lightbulb, count: assumptions.length },
      { id: "questions", label: "Questions", icon: HelpCircle, count: questions.length },
      { id: "documents", label: "Documents", icon: File, count: documents.length },
    ],
    [requirements.length, assumptions.length, questions.length, documents.length, functionalReqs.length, nfrReqs.length]
  );

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed left-0 top-1/2 -translate-y-1/2 bg-white border-r border-y border-gray-200 rounded-r-lg p-2 shadow-lg hover:bg-gray-50 transition-colors z-20"
        title="Show context panel"
        type="button"
      >
        <ChevronRight className="h-5 w-5 text-gray-600" />
      </button>
    );
  }

  return (
    <div className="w-80 bg-gray-50 border-r border-gray-200 flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white shrink-0">
        <h2 className="font-semibold text-gray-900">Context</h2>
        <button
          onClick={onToggle}
          className="p-1 hover:bg-gray-100 rounded transition-colors"
          title="Hide context panel"
          type="button"
        >
          <ChevronLeft className="h-5 w-5 text-gray-600" />
        </button>
      </div>

      <TabHeader tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />

      <div className="flex-1 overflow-hidden">
        <TabContent 
          activeTab={activeTab}
          requirements={requirements}
          assumptions={assumptions}
          questions={questions}
          documents={documents}
        />
      </div>
    </div>
  );
}

const leftContextPanel = memo(LeftContextPanelBase);
export { leftContextPanel as LeftContextPanel };

