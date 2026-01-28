import type { CostEstimate } from "../../../types/api";

interface CostEstimatesProps {
  readonly costs: readonly CostEstimate[];
}

function CostEstimateItem({ estimate }: { readonly estimate: CostEstimate }) {
  const currency = estimate.currencyCode !== "" ? estimate.currencyCode : "USD";
  const total = estimate.totalMonthlyCost;
  const lines = estimate.lineItems;

  return (
    <div
      className="bg-white p-4 rounded-md border border-gray-200"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="font-semibold text-gray-900">Cost Estimate</h4>
          <p className="text-sm text-gray-700 mt-1">
            {currency} {total.toFixed(2)} / month
            {estimate.variancePct !== undefined && estimate.variancePct !== 0
              ? ` (variance ${estimate.variancePct.toFixed(1)}%)`
              : ""}
          </p>
          {estimate.createdAt !== undefined && estimate.createdAt !== "" && (
            <p className="text-xs text-gray-500 mt-1">{estimate.createdAt}</p>
          )}
        </div>
        {estimate.id !== "" && <span className="text-xs text-gray-500">{estimate.id}</span>}
      </div>

      {lines.length > 0 && (
        <div className="mt-3 text-xs text-gray-600">
          <p className="font-medium">Line items</p>
          <ul className="list-disc list-inside">
            {lines.map((lineItem, lIdx: number) => (
              <li key={`li-${String(lIdx)}`}>
                {lineItem.name !== "" ? lineItem.name : "item"}: {currency} {lineItem.monthlyCost.toFixed(2)}
                {lineItem.unitOfMeasure !== undefined && lineItem.unitOfMeasure !== ""
                  ? ` (${lineItem.unitOfMeasure})`
                  : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function CostEstimates({ costs }: CostEstimatesProps) {
  if (costs.length === 0) {
    return <p className="text-gray-600">No cost estimates yet. Generate via Agent chat.</p>;
  }

  const sortedCosts = [...costs].sort((a, b) =>
    (a.createdAt ?? "").localeCompare(b.createdAt ?? "")
  );

  return (
    <div className="space-y-3">
      {sortedCosts.map((estimate, idx) => (
        <CostEstimateItem key={estimate.id !== "" ? estimate.id : `e-${idx}`} estimate={estimate} />
      ))}
    </div>
  );
}
