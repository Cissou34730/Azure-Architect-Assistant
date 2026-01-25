import { useState, useEffect } from "react";
import { ChevronLeft, ChevronRight, FileText, Network, TrendingUp } from "lucide-react";
import { Badge } from "../../../../components/common";
import { CostPieChart } from "../deliverables/charts";
import type { AdrArtifact, CostEstimate, FindingArtifact } from "../../../../types/api";

interface RightDeliverablesPanelProps {
  isOpen: boolean;
  onToggle: () => void;
  // Data
  adrs: readonly AdrArtifact[];
  diagrams: readonly Record<string, any>[];
  costEstimates: readonly CostEstimate[];
  findings: readonly FindingArtifact[];
  requirementsCount: number;
  onNavigateToDiagrams?: () => void;
  onNavigateToAdrs?: () => void;
  onNavigateToCosts?: () => void;
}

const STORAGE_KEY = "rightPanelOpen";

export function RightDeliverablesPanel({
  isOpen,
  onToggle,
  adrs,
  diagrams,
  costEstimates,
  findings,
  requirementsCount,
  onNavigateToDiagrams,
  onNavigateToAdrs,
  onNavigateToCosts,
}: RightDeliverablesPanelProps) {
  const [expandedSections, setExpandedSections] = useState({
    stats: true,
    diagrams: true,
    adrs: true,
    costs: true,
  });

  // Persist open/closed state
  useEffect(() => {
    if (isOpen !== undefined) {
      localStorage.setItem(STORAGE_KEY, String(isOpen));
    }
  }, [isOpen]);

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const latestCost = costEstimates.length > 0 ? costEstimates[costEstimates.length - 1] : null;
  const totalCost = latestCost?.totalMonthlyCost || 0;
  const currencyCode = latestCost?.currencyCode || "USD";

  const criticalFindings = findings.filter((f) => f.severity === "critical" || f.severity === "high").length;

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed right-0 top-1/2 -translate-y-1/2 bg-white border-l border-y border-gray-200 rounded-l-lg p-2 shadow-lg hover:bg-gray-50 transition-colors z-20"
        title="Show deliverables panel"
      >
        <ChevronLeft className="h-5 w-5 text-gray-600" />
      </button>
    );
  }

  return (
    <div className="w-80 bg-gray-50 border-l border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white shrink-0">
        <h2 className="font-semibold text-gray-900">Deliverables</h2>
        <button
          onClick={onToggle}
          className="p-1 hover:bg-gray-100 rounded transition-colors"
          title="Hide deliverables panel"
        >
          <ChevronRight className="h-5 w-5 text-gray-600" />
        </button>
      </div>

      {/* Content - Scrollable */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4 space-y-4">
          {/* Mini Stats */}
          <Section
            title="Key Metrics"
            expanded={expandedSections.stats}
            onToggle={() => toggleSection("stats")}
          >
            <div className="grid grid-cols-2 gap-3">
              <MiniStatCard
                icon={FileText}
                label="Requirements"
                value={requirementsCount}
                color="blue"
              />
              <MiniStatCard
                icon={FileText}
                label="ADRs"
                value={adrs.length}
                color="green"
              />
              <MiniStatCard
                icon={Network}
                label="Diagrams"
                value={diagrams.length}
                color="purple"
              />
              <MiniStatCard
                icon={TrendingUp}
                label="Findings"
                value={findings.length}
                badge={criticalFindings > 0 ? criticalFindings : undefined}
                color="amber"
              />
            </div>
          </Section>

          {/* Diagrams */}
          <Section
            title="Diagrams"
            expanded={expandedSections.diagrams}
            onToggle={() => toggleSection("diagrams")}
            count={diagrams.length}
            onViewAll={onNavigateToDiagrams}
          >
            {diagrams.length === 0 ? (
              <EmptyState message="No diagrams yet" />
            ) : (
              <div className="space-y-2">
                {diagrams.slice(0, 3).map((diagram, idx) => (
                  <DiagramPreviewCard key={diagram.id || idx} diagram={diagram} />
                ))}
                {diagrams.length > 3 && (
                  <button
                    onClick={onNavigateToDiagrams}
                    className="w-full text-center text-sm text-blue-600 hover:text-blue-700 py-2"
                  >
                    +{diagrams.length - 3} more diagrams
                  </button>
                )}
              </div>
            )}
          </Section>

          {/* ADRs */}
          <Section
            title="Architecture Decisions"
            expanded={expandedSections.adrs}
            onToggle={() => toggleSection("adrs")}
            count={adrs.length}
            onViewAll={onNavigateToAdrs}
          >
            {adrs.length === 0 ? (
              <EmptyState message="No ADRs yet" />
            ) : (
              <div className="space-y-2">
                {adrs.slice(0, 4).map((adr) => (
                  <AdrPreviewCard key={adr.id} adr={adr} />
                ))}
                {adrs.length > 4 && (
                  <button
                    onClick={onNavigateToAdrs}
                    className="w-full text-center text-sm text-blue-600 hover:text-blue-700 py-2"
                  >
                    +{adrs.length - 4} more ADRs
                  </button>
                )}
              </div>
            )}
          </Section>

          {/* Cost Summary */}
          <Section
            title="Cost Estimate"
            expanded={expandedSections.costs}
            onToggle={() => toggleSection("costs")}
            onViewAll={onNavigateToCosts}
          >
            {costEstimates.length === 0 ? (
              <EmptyState message="No cost estimates yet" />
            ) : (
              <div className="space-y-3">
                <div className="text-center py-2">
                  <div className="text-2xl font-bold text-gray-900">
                    {new Intl.NumberFormat("en-US", {
                      style: "currency",
                      currency: currencyCode,
                      minimumFractionDigits: 0,
                      maximumFractionDigits: 0,
                    }).format(totalCost)}
                  </div>
                  <div className="text-sm text-gray-500">per month</div>
                </div>
                {latestCost && latestCost.lineItems && latestCost.lineItems.length > 0 && (
                  <div className="h-48">
                    <CostPieChart lineItems={latestCost.lineItems} />
                  </div>
                )}
              </div>
            )}
          </Section>
        </div>
      </div>
    </div>
  );
}

// Section component with collapse/expand
interface SectionProps {
  title: string;
  expanded: boolean;
  onToggle: () => void;
  count?: number;
  onViewAll?: () => void;
  children: React.ReactNode;
}

function Section({ title, expanded, onToggle, count, onViewAll, children }: SectionProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100">
        <button
          onClick={onToggle}
          className="flex items-center gap-2 flex-1 text-left hover:text-blue-600 transition-colors"
        >
          <ChevronRight
            className={`h-4 w-4 transition-transform ${expanded ? "rotate-90" : ""}`}
          />
          <span className="text-sm font-medium text-gray-700">{title}</span>
          {count !== undefined && count > 0 && (
            <Badge size="sm">
              {count}
            </Badge>
          )}
        </button>
        {onViewAll && count && count > 0 && (
          <button
            onClick={onViewAll}
            className="text-xs text-blue-600 hover:text-blue-700 px-2"
          >
            View all
          </button>
        )}
      </div>
      {expanded && <div className="p-3">{children}</div>}
    </div>
  );
}

// Mini stat card
interface MiniStatCardProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  color: "blue" | "green" | "purple" | "amber";
  badge?: number;
}

function MiniStatCard({ icon: Icon, label, value, color, badge }: MiniStatCardProps) {
  const colorClasses = {
    blue: "bg-blue-50 text-blue-600",
    green: "bg-green-50 text-green-600",
    purple: "bg-purple-50 text-purple-600",
    amber: "bg-amber-50 text-amber-600",
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="flex items-center gap-2 mb-1">
        <div className={`p-1.5 rounded ${colorClasses[color]}`}>
          <Icon className="h-4 w-4" />
        </div>
        {badge !== undefined && (
          <Badge size="sm">
            {badge}
          </Badge>
        )}
      </div>
      <div className="text-xl font-bold text-gray-900">{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

// Diagram preview card
function DiagramPreviewCard({ diagram }: { diagram: Record<string, any> }) {
  return (
    <div className="bg-gray-50 rounded border border-gray-200 p-2 hover:bg-gray-100 transition-colors cursor-pointer">
      <div className="flex items-start gap-2">
        <Network className="h-4 w-4 text-gray-600 shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 truncate">
            {diagram.title || diagram.type || "Untitled Diagram"}
          </div>
          <div className="text-xs text-gray-500">
            {diagram.type ? diagram.type.toUpperCase() : "DIAGRAM"}
          </div>
        </div>
      </div>
    </div>
  );
}

// ADR preview card
function AdrPreviewCard({ adr }: { adr: AdrArtifact }) {
  const statusColors = {
    draft: "bg-gray-100 text-gray-700",
    accepted: "bg-green-100 text-green-700",
    rejected: "bg-red-100 text-red-700",
    superseded: "bg-yellow-100 text-yellow-700",
  };

  return (
    <div className="bg-gray-50 rounded border border-gray-200 p-2 hover:bg-gray-100 transition-colors cursor-pointer">
      <div className="flex items-start gap-2">
        <FileText className="h-4 w-4 text-gray-600 shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 truncate">{adr.title}</div>
          <div className="flex items-center gap-2 mt-1">
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                statusColors[adr.status] || statusColors.draft
              }`}
            >
              {adr.status}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

// Empty state
function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-4 text-sm text-gray-500">
      {message}
    </div>
  );
}
