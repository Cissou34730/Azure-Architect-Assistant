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
    card: "text-brand bg-brand-soft border-brand-line",
    progress: "bg-brand",
  },
  indigo: {
    card: "text-accent bg-accent-soft border-accent-line",
    progress: "bg-accent-soft",
  },
  purple: {
    card: "text-accent bg-accent-soft border-accent-line",
    progress: "bg-accent-soft",
  },
  pink: {
    card: "text-accent bg-accent-soft border-accent-line",
    progress: "bg-accent-soft",
  },
  green: {
    card: "text-success bg-success-soft border-success-line",
    progress: "bg-success",
  },
  red: {
    card: "text-danger bg-danger-soft border-danger-line",
    progress: "bg-danger-soft",
  },
  yellow: {
    card: "text-warning bg-warning-soft border-warning-line",
    progress: "bg-warning-soft",
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
        {icon !== undefined && icon !== "" && (
          <span className="text-xl">{icon}</span>
        )}
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
      {subtext !== undefined && subtext !== "" && (
        <div className="text-xs mt-1 opacity-75">{subtext}</div>
      )}
      {progress !== undefined && (
        <div className="mt-2 h-1.5 bg-card/50 rounded-pill overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${colors.progress}`}
            style={{ width: `${Math.min(Math.max(progress, 0), 100)}%` }}
          />
        </div>
      )}
    </div>
  );
}




