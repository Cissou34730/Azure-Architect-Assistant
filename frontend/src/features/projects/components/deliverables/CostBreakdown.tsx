import { useState, useMemo, lazy, Suspense } from "react";
import { DollarSign, Download } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent, EmptyState } from "../../../../components/common";
import type { CostEstimate } from "../../../../types/api";
import {
  ChartSkeleton,
  EstimateSelector,
  TotalCostDisplay,
  LineItemsTable,
  PricingGaps,
} from "./CostBreakdownParts";

// Lazy load the charts to reduce initial bundle size
// eslint-disable-next-line @typescript-eslint/naming-convention -- React lazy component must be PascalCase
const CostPieChart = lazy(() =>
  import("./charts/CostPieChart").then((m) => ({ default: m.CostPieChart })),
);

interface CostBreakdownProps {
  readonly costEstimates: readonly CostEstimate[];
}

function handleExportCSV(estimate: CostEstimate): void {
  if (estimate.lineItems.length === 0) return;

  const headers = [
    "Service",
    "Monthly Quantity",
    "Unit Price",
    "Monthly Cost",
    "Unit",
  ];
  const rows = estimate.lineItems.map((item) => [
    item.name,
    String(item.monthlyQuantity),
    String(item.unitPrice),
    String(item.monthlyCost),
    item.unitOfMeasure ?? "",
  ]);

  const csv = [headers, ...rows].map((row) => row.join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `cost-estimate-${estimate.createdAt ?? "export"}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export function CostBreakdown({ costEstimates }: CostBreakdownProps) {
  const [selectedEstimate, setSelectedEstimate] = useState<CostEstimate | null>(
    costEstimates.length > 0
      ? (costEstimates[costEstimates.length - 1] ?? null)
      : null,
  );
  const [expandedLineItems, setExpandedLineItems] = useState(false);

  const sortedEstimates = useMemo(() => {
    return [...costEstimates].sort((a, b) => {
      const dateA = a.createdAt ?? "";
      const dateB = b.createdAt ?? "";
      return dateB.localeCompare(dateA);
    });
  }, [costEstimates]);

  if (costEstimates.length === 0) {
    return (
      <EmptyState
        icon={DollarSign}
        title="No cost estimates yet"
        description="Request cost estimation using the Workspace chat"
        action={
          <button
            type="button"
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            Go to Workspace
          </button>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <EstimateSelector
        estimates={sortedEstimates}
        selectedId={selectedEstimate?.id}
        onSelect={setSelectedEstimate}
      />

      {selectedEstimate !== null && (
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle>Cost Estimate</CardTitle>
                {selectedEstimate.createdAt !== undefined && (
                  <p className="text-sm text-gray-600 mt-1">
                    Generated:{" "}
                    {new Date(selectedEstimate.createdAt).toLocaleString()}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => {
                  handleExportCSV(selectedEstimate);
                }}
                className="flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-sm"
              >
                <Download className="h-4 w-4" />
                Export CSV
              </button>
            </div>
          </CardHeader>

          <CardContent>
            <div className="space-y-6">
              <TotalCostDisplay estimate={selectedEstimate} />

              {selectedEstimate.lineItems.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-4">
                    Cost by Service
                  </h3>
                  <Suspense fallback={<ChartSkeleton />}>
                    <CostPieChart lineItems={selectedEstimate.lineItems} />
                  </Suspense>
                </div>
              )}

              <LineItemsTable
                estimate={selectedEstimate}
                expanded={expandedLineItems}
                onToggle={() => {
                  setExpandedLineItems(!expandedLineItems);
                }}
              />

              {selectedEstimate.pricingGaps.length > 0 && (
                <PricingGaps gaps={selectedEstimate.pricingGaps} />
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
