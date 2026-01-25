import { FileText, AlertTriangle, DollarSign, CheckSquare } from "lucide-react";
import { StatCard } from "../../../../components/common";

interface HeroStatsProps {
  requirementsCount: number;
  adrsCount: number;
  findingsCount: number;
  monthlyCost: number;
  currencyCode?: string;
}

export function HeroStats({
  requirementsCount,
  adrsCount,
  findingsCount,
  monthlyCost,
  currencyCode = "USD",
}: HeroStatsProps) {
  const formatCurrency = (amount: number) => {
    if (amount >= 1000) {
      return `${(amount / 1000).toFixed(1)}k`;
    }
    return amount.toFixed(0);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        icon={CheckSquare}
        label="Requirements"
        value={requirementsCount}
        iconColor="text-blue-600"
      />
      <StatCard
        icon={FileText}
        label="ADRs"
        value={adrsCount}
        iconColor="text-purple-600"
      />
      <StatCard
        icon={AlertTriangle}
        label="Findings"
        value={findingsCount}
        iconColor={findingsCount > 0 ? "text-amber-600" : "text-green-600"}
      />
      <StatCard
        icon={DollarSign}
        label="Monthly Cost"
        value={monthlyCost > 0 ? `${currencyCode} ${formatCurrency(monthlyCost)}` : "—"}
        iconColor="text-green-600"
      />
    </div>
  );
}
