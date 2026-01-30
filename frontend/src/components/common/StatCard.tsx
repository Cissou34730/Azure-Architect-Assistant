import { LucideIcon } from "lucide-react";
import { Card, CardContent } from "./Card";

interface StatCardProps {
  icon: LucideIcon;
  label: string;
  value: string | number;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  className?: string;
  iconColor?: string;
}

export function StatCard({
  icon: iconProp,
  label,
  value,
  trend,
  className = "",
  iconColor = "text-blue-600",
}: StatCardProps) {
// eslint-disable-next-line @typescript-eslint/naming-convention
  const Icon = iconProp;

  return (
    <Card className={className} hover>
      <CardContent className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600">{label}</p>
          <div className="flex items-baseline mt-1">
            <p className="text-2xl font-semibold text-gray-900">{value}</p>
            {trend !== undefined && (
              <span
                className={`ml-2 text-sm font-medium ${
                  trend.isPositive ? "text-green-600" : "text-red-600"
                }`}
              >
                {trend.isPositive ? "+" : ""}
                {trend.value}%
              </span>
            )}
          </div>
        </div>
        <div className={`p-3 rounded-full bg-opacity-10 ${iconColor}`}>
          <Icon className={`h-6 w-6 ${iconColor}`} />
        </div>
      </CardContent>
    </Card>
  );
}
