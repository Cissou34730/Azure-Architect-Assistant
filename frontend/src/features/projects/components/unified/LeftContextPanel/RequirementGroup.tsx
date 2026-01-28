import type { Requirement } from "../../../../../types/api";

interface RequirementGroupProps {
  readonly title: string;
  readonly requirements: readonly Requirement[];
  readonly color: "blue" | "green" | "purple" | "gray";
}

export function RequirementGroup({
  title,
  requirements,
  color,
}: RequirementGroupProps) {
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
            key={req.id ?? `req-${idx}`}
            className={`text-sm p-3 rounded-lg border ${colorClasses}`}
          >
            {req.text}
          </div>
        ))}
      </div>
    </div>
  );
}
