import { Calculator } from "lucide-react";
import type { CostEstimate } from "../../../../../types/api";
import { BaseCard } from "./BaseCard";

interface CostCardProps {
  readonly estimate: CostEstimate;
  readonly onClick: () => void;
}

export function CostCard({ estimate, onClick }: CostCardProps) {
  const dateStr = estimate.createdAt !== undefined 
    ? new Date(estimate.createdAt).toLocaleDateString() 
    : "Recent";
  
  return (
    <BaseCard
      title="Architecture Cost Summary"
      date={dateStr}
      onClick={onClick}
    >
      <div className="flex items-center justify-between mt-1">
        <div className="flex items-center text-blue-600">
          <Calculator className="h-3 w-3 mr-1" />
          <span className="text-xs font-semibold">
            {new Intl.NumberFormat("en-US", {
              style: "currency",
              currency: estimate.currencyCode !== "" 
                ? estimate.currencyCode 
                : "USD",
            }).format(estimate.totalMonthlyCost)}
          </span>
          <span className="text-[10px] text-gray-400 ml-1">/mo</span>
        </div>
      </div>
    </BaseCard>
  );
}
