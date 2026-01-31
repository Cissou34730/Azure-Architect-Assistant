import { useMemo } from "react";
import { GroupedVirtuoso } from "react-virtuoso";
import type { Requirement } from "../../../../../types/api";

interface RequirementsTabProps {
  readonly requirements: readonly Requirement[];
}

type GroupColor = "blue" | "green" | "purple" | "gray";

interface GroupTitle {
  readonly title: string;
  readonly color: GroupColor;
}

interface GroupConfig extends GroupTitle {
  readonly items: readonly Requirement[];
}

const colorClassesMap: Record<GroupColor, string> = {
  blue: "text-blue-700 bg-blue-50 border-blue-200",
  green: "text-green-700 bg-green-50 border-green-200",
  purple: "text-purple-700 bg-purple-50 border-purple-200",
  gray: "text-gray-700 bg-gray-50 border-gray-200",
};

export function RequirementsTab({ requirements }: RequirementsTabProps) {
  // Task 4.1: Memoize sorted requirements
  const sortedRequirements = useMemo(() => {
    return [...requirements].sort((a, b) =>
      (a.text ?? "").localeCompare(b.text ?? "")
    );
  }, [requirements]);

  const { groupedItems, groupCounts, groupTitles } = useMemo((): {
    groupedItems: readonly Requirement[];
    groupCounts: readonly number[];
    groupTitles: readonly GroupTitle[];
  } => {
    const business = sortedRequirements.filter(
      (r) => r.category?.toLowerCase() === "business"
    );
    const functional = sortedRequirements.filter(
      (r) => r.category?.toLowerCase() === "functional"
    );
    const nfr = sortedRequirements.filter(
      (r) => r.category?.toLowerCase() === "nfr"
    );
    const other = sortedRequirements.filter((r) => {
      const cat = r.category?.toLowerCase();
      return cat !== "business" && cat !== "functional" && cat !== "nfr";
    });

    const groups: readonly GroupConfig[] = [
      { title: "Business", items: business, color: "blue" },
      { title: "Functional", items: functional, color: "green" },
      { title: "Non-Functional", items: nfr, color: "purple" },
      { title: "Other", items: other, color: "gray" },
    ].filter((group) => group.items.length > 0);

    return {
      groupedItems: groups.flatMap((group) => group.items),
      groupCounts: groups.map((group) => group.items.length),
      groupTitles: groups.map((group) => ({
        title: group.title,
        color: group.color,
      })),
    };
  }, [sortedRequirements]);

  if (requirements.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500">
        No requirements yet. Start chatting to identify requirements.
      </div>
    );
  }

  return (
    <div className="h-full">
      <GroupedVirtuoso
        groupCounts={groupCounts}
        className="panel-scroll"
        groupContent={(index) => {
          const { title } = groupTitles[index];
          return (
            <div className="bg-white px-4 py-2">
              <h3 className="text-xs font-semibold text-gray-900 uppercase tracking-wide">
                {title} ({groupCounts[index]})
              </h3>
            </div>
          );
        }}
        itemContent={(index) => {
          const req = groupedItems[index];
          // Determine color based on group index logic or item property
          // A bit tricky with flat map, let's find which group this index belongs to
          let currentGroupIdx = 0;
          let sum = 0;
          for (let i = 0; i < groupCounts.length; i++) {
            sum += groupCounts[i];
            if (index < sum) {
              currentGroupIdx = i;
              break;
            }
          }
          const { color } = groupTitles[currentGroupIdx];
          const text =
            req.text !== undefined && req.text !== ""
              ? req.text
              : "Untitled requirement";

          return (
            <div className="px-4 py-1">
              <div className={`text-sm p-3 rounded-lg border ${colorClassesMap[color]}`}>
                {text}
              </div>
            </div>
          );
        }}
        style={{ height: "100%" }}
      />
    </div>
  );
}

