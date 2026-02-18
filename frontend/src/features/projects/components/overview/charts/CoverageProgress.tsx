interface CoverageProgressProps {
  percentage: number;
}

export function CoverageProgress({ percentage }: CoverageProgressProps) {
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  let color = "var(--color-success)"; // green
  if (percentage < 33) color = "var(--color-danger)"; // red
  else if (percentage < 66) color = "var(--color-warning)"; // amber

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="160" height="160" className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx="80"
          cy="80"
          r={radius}
          stroke="var(--color-border)"
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
        <span className="text-3xl font-bold text-foreground">{percentage}%</span>
        <span className="text-xs text-secondary">Complete</span>
      </div>
    </div>
  );
}

