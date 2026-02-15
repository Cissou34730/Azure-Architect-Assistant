import { useEffect, memo } from "react";
import { 
  ChevronLeft,
  Sparkles
} from "lucide-react";
import { useRightPanel } from "./RightDeliverablesPanel/useRightPanel";
import { DiagramsSection } from "./RightDeliverablesPanel/DiagramsSection";
import { AdrsSection } from "./RightDeliverablesPanel/AdrsSection";
import { FindingsSection } from "./RightDeliverablesPanel/FindingsSection";
import { CostsSection } from "./RightDeliverablesPanel/CostsSection";
import { PanelHeader } from "./RightDeliverablesPanel/PanelHeader";
import { useRenderCount } from "../../../../hooks/useRenderCount";

interface RightDeliverablesPanelProps {
  readonly isOpen: boolean;
  readonly onToggle: () => void;
  readonly onNavigateToDiagrams?: () => void;
  readonly onNavigateToAdrs?: () => void;
  readonly onNavigateToCosts?: () => void;
}

const STORAGE_KEY = "rightPanelOpen";

function RightDeliverablesPanel({ 
  isOpen, 
  onToggle,
  onNavigateToDiagrams,
  onNavigateToAdrs,
  onNavigateToCosts
}: RightDeliverablesPanelProps) {
  useRenderCount("RightDeliverablesPanel");
  const {
    expandedSections,
    searchQuery,
    setSearchQuery,
    toggleSection,
    adrs,
    findings,
    costs,
    diagrams,
    reqCount
  } = useRightPanel();

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(isOpen));
  }, [isOpen]);

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed right-0 top-1/2 -translate-y-1/2 bg-card border-l border-y border-border rounded-l-lg p-2 shadow-lg hover:bg-surface transition-colors z-20"
        title="Show deliverables panel"
      >
        <ChevronLeft className="h-5 w-5 text-secondary" />
      </button>
    );
  }

  return (
    <div className="w-80 flex flex-col h-full bg-card border-l border-border shadow-sm animate-in slide-in-from-right duration-300">
      <PanelHeader 
        onToggle={onToggle}
        adrCount={adrs.length}
        findingCount={findings.length}
        requirementCount={reqCount}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      <div className="flex-1 overflow-y-auto p-3 space-y-3 custom-scrollbar">
        <DiagramsSection 
          diagrams={diagrams}
          expanded={expandedSections.has("diagrams")}
          onToggle={() => { toggleSection("diagrams"); }}
          onNavigate={onNavigateToDiagrams}
        />

        <AdrsSection 
          adrs={adrs}
          expanded={expandedSections.has("adrs")}
          onToggle={() => { toggleSection("adrs"); }}
          onNavigate={onNavigateToAdrs}
        />

        <FindingsSection 
          findings={findings}
          expanded={expandedSections.has("findings")}
          onToggle={() => { toggleSection("findings"); }}
        />

        <CostsSection 
          costs={costs}
          expanded={expandedSections.has("costs")}
          onToggle={() => { toggleSection("costs"); }}
          onNavigate={onNavigateToCosts}
        />
      </div>

      <div className="p-3 bg-surface border-t border-border">
        <div className="flex items-center gap-2 p-3 bg-card rounded-lg border border-brand-line shadow-sm">
          <div className="h-7 w-7 rounded-md bg-brand flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-inverse" />
          </div>
          <div className="flex-1">
            <p className="text-[10px] font-medium text-brand-strong uppercase tracking-wider">Copilot Recommendation</p>
            <p className="text-[11px] text-secondary font-medium">Ready for cost optimization?</p>
          </div>
          <button className="text-[11px] font-bold text-brand hover:text-brand-strong">
            Fix
          </button>
        </div>
      </div>
    </div>
  );
}

const rightDeliverablesPanel = memo(RightDeliverablesPanel);
export { rightDeliverablesPanel as RightDeliverablesPanel };



