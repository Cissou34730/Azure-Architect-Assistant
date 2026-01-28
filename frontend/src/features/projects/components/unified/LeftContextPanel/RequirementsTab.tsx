import type { Requirement } from "../../../../../types/api";
import { RequirementGroup } from "./RequirementGroup";

interface RequirementsTabProps {
  readonly requirements: readonly Requirement[];
}

export function RequirementsTab({ requirements }: RequirementsTabProps) {
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
