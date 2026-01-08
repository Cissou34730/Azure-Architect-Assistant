/**
 * Reusable Metric Card Component
 * Displays a single metric with optional progress bar
 */

type MetricColor =
  | "blue"
  | "indigo"
  | "purple"
  | "pink"
  | "green"
  | "red"
  | "yellow";

interface MetricCardProps {
  label: string;
  value: number | string;
  total?: number;
  progress?: number;
  subtext?: string;
  icon?: string;
  color?: MetricColor;
}

// Fixed color mapping to avoid dynamic class generation issues with Tailwind
const COLOR_CLASSES: Record<MetricColor, { card: string; progress: string }> = {
  blue: {
    card: "text-blue-600 bg-blue-50 border-blue-200",
    progress: "bg-blue-500",
  },
  indigo: {
    card: "text-indigo-600 bg-indigo-50 border-indigo-200",
    progress: "bg-indigo-500",
  },
  purple: {
    card: "text-purple-600 bg-purple-50 border-purple-200",
    progress: "bg-purple-500",
  },
  pink: {
    card: "text-pink-600 bg-pink-50 border-pink-200",
    progress: "bg-pink-500",
  },
  green: {
    card: "text-green-600 bg-green-50 border-green-200",
    progress: "bg-green-500",
  },
  red: {
    card: "text-red-600 bg-red-50 border-red-200",
    progress: "bg-red-500",
  },
  yellow: {
    card: "text-yellow-600 bg-yellow-50 border-yellow-200",
    progress: "bg-yellow-500",
  },
};

export function MetricCard({
  label,
  value,
  total,
  progress,
  subtext,
  icon,
  color = "blue",
}: MetricCardProps) {
  const colors = COLOR_CLASSES[color];

  return (
    <div className={`p-4 rounded-card border ${colors.card}`}>
      <div className="flex items-center gap-2 mb-2">
        {icon && <span className="text-xl">{icon}</span>}
        <div className="text-xs font-medium uppercase tracking-wide opacity-75">
          {label}
        </div>
      </div>
      <div className="text-2xl font-bold">
        {typeof value === "number" ? value.toLocaleString() : value}
        {total !== undefined && (
          <span className="text-sm font-normal opacity-60">
            {" / "}
            {total.toLocaleString()}
          </span>
        )}
      </div>
      {subtext && <div className="text-xs mt-1 opacity-75">{subtext}</div>}
      {progress !== undefined && (
        <div className="mt-2 h-1.5 bg-white/50 rounded-pill overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${colors.progress}`}
            style={{ width: `${Math.min(Math.max(progress, 0), 100)}%` }}
          />
        </div>
      )}
    </div>
  );
}
