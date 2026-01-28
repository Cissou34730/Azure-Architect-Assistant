import { useState, useMemo } from "react";
import { DollarSign, Download, ChevronDown, ChevronRight, AlertTriangle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent, Badge, EmptyState } from "../../../../components/common";
import { CostPieChart } from "./charts";
import type { CostEstimate } from "../../../../types/api";

interface CostBreakdownProps {
  readonly costEstimates: readonly CostEstimate[];
}

interface EstimateSelectorProps {
  readonly estimates: readonly CostEstimate[];
  readonly selectedId: string | undefined;
  readonly onSelect: (estimate: CostEstimate) => void;
}

function EstimateSelector({
  estimates,
  selectedId,
  onSelect,
}: EstimateSelectorProps) {
  if (estimates.length <= 1) return null;

  return (
    <div className="flex gap-2 flex-wrap">
      {estimates.map((estimate, idx) => {
        const isSelected = selectedId === estimate.id;
        return (
          <button
            key={estimate.id}
            type="button"
            onClick={() => {
              onSelect(estimate);
            }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              isSelected
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {estimate.createdAt !== undefined
              ? new Date(estimate.createdAt).toLocaleDateString()
              : `Estimate ${estimates.length - idx}`}
          </button>
        );
      })}
    </div>
  );
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

interface TotalCostDisplayProps {
  readonly estimate: CostEstimate;
}

function TotalCostDisplay({ estimate }: TotalCostDisplayProps) {
  return (
    <div className="text-center py-6 border-b border-gray-200">
      <div className="text-5xl font-bold text-gray-900 mb-2">
        {estimate.currencyCode} {estimate.totalMonthlyCost.toFixed(2)}
      </div>
      <div className="text-sm text-gray-600">Per Month</div>
      {estimate.variancePct !== undefined && (
        <Badge
          variant={estimate.variancePct > 0 ? "error" : "success"}
          size="md"
          className="mt-2"
        >
          {estimate.variancePct > 0 ? "+" : ""}
          {estimate.variancePct.toFixed(1)}% variance
        </Badge>
      )}
    </div>
  );
}

interface LineItemsTableProps {
  readonly estimate: CostEstimate;
  readonly expanded: boolean;
  readonly onToggle: () => void;
}

function LineItemsTable({ estimate, expanded, onToggle }: LineItemsTableProps) {
  if (estimate.lineItems.length === 0) return null;

  return (
    <div>
      <button
        type="button"
        onClick={onToggle}
        className="flex items-center gap-2 w-full text-left text-sm font-semibold text-gray-900 hover:text-gray-700 transition-colors mb-4"
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4" />
        ) : (
          <ChevronRight className="h-4 w-4" />
        )}
        Line Items ({estimate.lineItems.length})
      </button>

      {expanded && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Service
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">
                  Quantity
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">
                  Unit Price
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">
                  Monthly Cost
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {estimate.lineItems.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-900">{item.name}</td>
                  <td className="px-4 py-3 text-right text-gray-600">
                    {item.monthlyQuantity}{" "}
                    <span className="text-xs text-gray-500">
                      {item.unitOfMeasure ?? "units"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600">
                    {estimate.currencyCode} {item.unitPrice.toFixed(4)}
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-gray-900">
                    {estimate.currencyCode} {item.monthlyCost.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

interface PricingGapsProps {
  // eslint-disable-next-line @typescript-eslint/no-restricted-types -- Backend returns dynamic pricing gap structure
  readonly gaps: readonly Record<string, unknown>[];
}

function PricingGaps({ gaps }: PricingGapsProps) {
  if (gaps.length === 0) return null;

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-amber-900 mb-2">
            Pricing Gaps ({gaps.length})
          </h4>
          <div className="space-y-1">            {/* eslint-disable-next-line react/no-array-index-key -- Gap objects have no stable ID */}            {gaps.map((gap, idx) => (
              <div key={idx} className="text-sm text-amber-800">
                <span className="font-medium">
                  {typeof gap.name === "string" ? gap.name : "Unknown"}:
                </span>{" "}
                {typeof gap.reason === "string"
                  ? gap.reason
                  : "Pricing information unavailable"}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
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
                  <CostPieChart lineItems={selectedEstimate.lineItems} />
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
