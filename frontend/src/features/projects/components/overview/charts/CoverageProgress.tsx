interface CoverageProgressProps {
  percentage: number;
}

export function CoverageProgress({ percentage }: CoverageProgressProps) {
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  let color = "#10b981"; // green
  if (percentage < 33) color = "#ef4444"; // red
  else if (percentage < 66) color = "#f59e0b"; // amber

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="160" height="160" className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx="80"
          cy="80"
          r={radius}
          stroke="#e5e7eb"
          strokeWidth="12"
          fill="none"
        />
        {/* Progress circle */}
        <circle
          cx="80"
          cy="80"
          r={radius}
          stroke={color}
          strokeWidth="12"
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-500"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold text-gray-900">{percentage}%</span>
        <span className="text-xs text-gray-600">Complete</span>
      </div>
    </div>
  );
}
