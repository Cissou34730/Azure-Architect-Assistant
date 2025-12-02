/**
 * Reusable Metric Card Component
 * Displays a single metric with optional progress bar
 */

interface MetricCardProps {
  label: string;
  value: number | string;
  total?: number;
  progress?: number;
  subtext?: string;
  icon?: string;
  color?: 'blue' | 'indigo' | 'purple' | 'pink' | 'green' | 'red' | 'yellow';
}

export function MetricCard({ 
  label, 
  value, 
  total, 
  progress, 
  subtext, 
  icon, 
  color = 'blue' 
}: MetricCardProps) {
  const colorClass = `text-${color}-600 bg-${color}-50 border-${color}-200`;
  const progressColorClass = `bg-${color}-500`;
  
  return (
    <div className={`p-4 rounded-card border ${colorClass}`}>
      <div className="flex items-center gap-2 mb-2">
        {icon && <span className="text-xl">{icon}</span>}
        <div className="text-xs font-medium uppercase tracking-wide opacity-75">
          {label}
        </div>
      </div>
      <div className="text-2xl font-bold">
        {typeof value === 'number' ? value.toLocaleString() : value}
        {total !== undefined && (
          <span className="text-sm font-normal opacity-60">
            {' / '}
            {total.toLocaleString()}
          </span>
        )}
      </div>
      {subtext && (
        <div className="text-xs mt-1 opacity-75">{subtext}</div>
      )}
      {progress !== undefined && (
        <div className="mt-2 h-1.5 bg-white/50 rounded-pill overflow-hidden">
          <div 
            className={`h-full transition-all duration-300 ${progressColorClass}`}
            style={{ width: `${Math.min(Math.max(progress, 0), 100)}%` }}
          />
        </div>
      )}
    </div>
  );
}
