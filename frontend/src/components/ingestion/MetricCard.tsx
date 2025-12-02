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
  const colorClasses = {
    blue: 'text-blue-600 bg-blue-50 border-blue-200',
    indigo: 'text-indigo-600 bg-indigo-50 border-indigo-200',
    purple: 'text-purple-600 bg-purple-50 border-purple-200',
    pink: 'text-pink-600 bg-pink-50 border-pink-200',
    green: 'text-green-600 bg-green-50 border-green-200',
    red: 'text-red-600 bg-red-50 border-red-200',
    yellow: 'text-yellow-600 bg-yellow-50 border-yellow-200',
  };
  
  const progressColorClasses = {
    blue: 'bg-blue-500',
    indigo: 'bg-indigo-500',
    purple: 'bg-purple-500',
    pink: 'bg-pink-500',
    green: 'bg-green-500',
    red: 'bg-red-500',
    yellow: 'bg-yellow-500',
  };
  
  return (
    <div className={`p-4 rounded-lg border ${colorClasses[color]}`}>
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
        <div className="mt-2 h-1.5 bg-white/50 rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all duration-300 ${progressColorClasses[color]}`}
            style={{ width: `${Math.min(Math.max(progress, 0), 100)}%` }}
          />
        </div>
      )}
    </div>
  );
}
