import { useState } from "react";
import { ChevronDown, ChevronRight, AlertCircle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent, Badge } from "../../../../components/common";

interface Requirement {
  readonly id?: string;
  readonly category?: string;
  readonly text?: string;
  readonly ambiguity?: { readonly isAmbiguous?: boolean; readonly notes?: string };
  readonly sources?: readonly { readonly documentId?: string; readonly fileName?: string; readonly excerpt?: string }[];
}

interface RequirementsCardProps {
  readonly requirements: readonly Requirement[];
}

interface GroupedRequirements {
  readonly business: Requirement[];
  readonly functional: Requirement[];
  readonly nfr: Requirement[];
  readonly other: Requirement[];
}

interface RequirementItemProps {
  readonly requirement: Requirement;
  readonly groupKey: string;
  readonly index: number;
}

interface RequirementSourcesProps {
  readonly sources: readonly {
    readonly documentId?: string;
    readonly fileName?: string;
    readonly excerpt?: string;
  }[];
}

function RequirementSources({ sources }: RequirementSourcesProps) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-2 ml-6 flex flex-wrap gap-1">
      {sources.slice(0, 3).map((src) => {
        const sourceLabel =
          src.fileName !== undefined && src.fileName !== ""
            ? src.fileName
            : src.documentId !== undefined && src.documentId !== ""
              ? src.documentId
              : "Source";
        return (
          <Badge key={`${sourceLabel}-${src.excerpt ?? ""}`} variant="info" size="sm">
            {sourceLabel}
          </Badge>
        );
      })}
      {sources.length > 3 && (
        <Badge variant="default" size="sm">
          +{sources.length - 3} more
        </Badge>
      )}
    </div>
  );
}

function RequirementItem({
  requirement,
  groupKey,
  index,
}: RequirementItemProps) {
  const isAmbiguous = requirement.ambiguity?.isAmbiguous === true;
  const text =
    requirement.text !== undefined && requirement.text !== ""
      ? requirement.text
      : "Untitled requirement";

  return (
    <div
      key={requirement.id ?? `${groupKey}-${index}`}
      className="bg-gray-50 rounded-md p-3 text-sm"
    >
      <div className="flex items-start gap-2">
        {isAmbiguous && (
          <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
        )}
        <p className="text-gray-900 flex-1">{text}</p>
      </div>
      {isAmbiguous &&
        requirement.ambiguity.notes !== undefined &&
        requirement.ambiguity.notes !== "" && (
          <p className="text-xs text-amber-700 mt-1 ml-6">
            {requirement.ambiguity.notes}
          </p>
        )}
      {requirement.sources !== undefined && (
        <RequirementSources sources={requirement.sources} />
      )}
    </div>
  );
}

interface RequirementCategoryProps {
  readonly label: string;
  readonly categoryKey: string;
  readonly items: readonly Requirement[];
  readonly isExpanded: boolean;
  readonly onToggle: (key: string) => void;
}

function RequirementCategory({
  label,
  categoryKey,
  items,
  isExpanded,
  onToggle,
}: RequirementCategoryProps) {
  const ambiguousCount = items.filter((r) => r.ambiguity?.isAmbiguous === true).length;

  return (
    <div key={categoryKey} className="border-b border-gray-100 last:border-b-0">
      <button
        type="button"
        onClick={() => {
          onToggle(categoryKey);
        }}
        className="w-full flex items-center justify-between py-3 px-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-gray-500" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-500" />
          )}
          <span className="font-medium text-gray-900">{label}</span>
          <Badge variant="default" size="sm">
            {items.length}
          </Badge>
          {ambiguousCount > 0 && (
            <Badge variant="warning" size="sm">
              {ambiguousCount} ambiguous
            </Badge>
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="px-4 pb-3 space-y-2">
          {items.length === 0 ? (
            <p className="text-sm text-gray-500 italic">No requirements in this category</p>
          ) : (
            items.map((req, idx) => (
              <RequirementItem
                key={req.id ?? `${categoryKey}-${idx}`}
                requirement={req}
                groupKey={categoryKey}
                index={idx}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}

export function RequirementsCard({ requirements }: RequirementsCardProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(["business"]),
  );

  const grouped: GroupedRequirements = {
    business: [],
    functional: [],
    nfr: [],
    other: [],
  };

  for (const req of requirements) {
    const categoryName = (req.category ?? "").toLowerCase();
    if (categoryName === "business") grouped.business.push(req);
    else if (categoryName === "functional") grouped.functional.push(req);
    else if (categoryName === "nfr") grouped.nfr.push(req);
    else grouped.other.push(req);
  }

  const toggleGroup = (groupKey: string) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(groupKey)) {
      newExpanded.delete(groupKey);
    } else {
      newExpanded.add(groupKey);
    }
    setExpandedGroups(newExpanded);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Requirements</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {requirements.length === 0 ? (
          <div className="px-6 py-8 text-center text-gray-500">
            No requirements yet. Upload and analyze documents to extract requirements.
          </div>
        ) : (
          <div>
            <RequirementCategory
              label="Business"
              categoryKey="business"
              items={grouped.business}
              isExpanded={expandedGroups.has("business")}
              onToggle={toggleGroup}
            />
            <RequirementCategory
              label="Functional"
              categoryKey="functional"
              items={grouped.functional}
              isExpanded={expandedGroups.has("functional")}
              onToggle={toggleGroup}
            />
            <RequirementCategory
              label="Non-Functional"
              categoryKey="nfr"
              items={grouped.nfr}
              isExpanded={expandedGroups.has("nfr")}
              onToggle={toggleGroup}
            />
            <RequirementCategory
              label="Other"
              categoryKey="other"
              items={grouped.other}
              isExpanded={expandedGroups.has("other")}
              onToggle={toggleGroup}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
