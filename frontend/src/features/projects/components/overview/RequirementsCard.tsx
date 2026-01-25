import { useState } from "react";
import { ChevronDown, ChevronRight, AlertCircle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent, Badge } from "../../../../components/common";

interface Requirement {
  readonly id?: string;
  readonly category?: string;
  readonly text?: string;
  readonly ambiguity?: { readonly isAmbiguous?: boolean; readonly notes?: string };
  readonly sources?: ReadonlyArray<{ readonly documentId?: string; readonly fileName?: string; readonly excerpt?: string }>;
}

interface RequirementsCardProps {
  requirements: readonly Requirement[];
}

interface GroupedRequirements {
  business: Requirement[];
  functional: Requirement[];
  nfr: Requirement[];
  other: Requirement[];
}

export function RequirementsCard({ requirements }: RequirementsCardProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(["business"]));

  const grouped: GroupedRequirements = {
    business: [],
    functional: [],
    nfr: [],
    other: [],
  };

  for (const req of requirements) {
    const category = (req?.category || "").toLowerCase();
    if (category === "business") grouped.business.push(req);
    else if (category === "functional") grouped.functional.push(req);
    else if (category === "nfr") grouped.nfr.push(req);
    else grouped.other.push(req);
  }

  const toggleGroup = (group: string) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(group)) {
      newExpanded.delete(group);
    } else {
      newExpanded.add(group);
    }
    setExpandedGroups(newExpanded);
  };

  const renderGroup = (label: string, key: string, items: Requirement[]) => {
    const isExpanded = expandedGroups.has(key);
    const ambiguousCount = items.filter(r => r.ambiguity?.isAmbiguous).length;

    return (
      <div key={key} className="border-b border-gray-100 last:border-b-0">
        <button
          onClick={() => toggleGroup(key)}
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
              items.map((req, idx) => {
                const isAmbiguous = req.ambiguity?.isAmbiguous;
                const text = req.text || "Untitled requirement";

                return (
                  <div
                    key={req.id || `${key}-${idx}`}
                    className="bg-gray-50 rounded-md p-3 text-sm"
                  >
                    <div className="flex items-start gap-2">
                      {isAmbiguous && (
                      <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                      )}
                      <p className="text-gray-900 flex-1">{text}</p>
                    </div>
                    {isAmbiguous && req.ambiguity?.notes && (
                      <p className="text-xs text-amber-700 mt-1 ml-6">
                        {req.ambiguity.notes}
                      </p>
                    )}
                    {req.sources && req.sources.length > 0 && (
                      <div className="mt-2 ml-6 flex flex-wrap gap-1">
                        {req.sources.slice(0, 3).map((src, srcIdx) => (
                          <Badge key={srcIdx} variant="info" size="sm">
                            {src.fileName || src.documentId || "Source"}
                          </Badge>
                        ))}
                        {req.sources.length > 3 && (
                          <Badge variant="default" size="sm">
                            +{req.sources.length - 3} more
                          </Badge>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    );
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
            {renderGroup("Business", "business", grouped.business)}
            {renderGroup("Functional", "functional", grouped.functional)}
            {renderGroup("Non-Functional", "nfr", grouped.nfr)}
            {renderGroup("Other", "other", grouped.other)}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
