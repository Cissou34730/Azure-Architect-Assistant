import { useState } from "react";
import { DollarSign, Download, ChevronDown, ChevronRight, AlertTriangle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent, Badge, EmptyState } from "../../../../components/common";
import { CostPieChart } from "./charts";
import type { CostEstimate } from "../../../../types/api";

interface CostBreakdownProps {
  costEstimates: readonly CostEstimate[];
}

export function CostBreakdown({ costEstimates }: CostBreakdownProps) {
  const [selectedEstimate, setSelectedEstimate] = useState<CostEstimate | null>(
    costEstimates.length > 0 ? costEstimates[costEstimates.length - 1] : null
  );
  const [expandedLineItems, setExpandedLineItems] = useState(false);

  if (costEstimates.length === 0) {
    return (
      <EmptyState
        icon={DollarSign}
        title="No cost estimates yet"
        description="Request cost estimation using the Workspace chat"
        action={
          <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm">
            Go to Workspace
          </button>
        }
      />
    );
  }

  const sortedEstimates = [...costEstimates].sort((a, b) => {
    const dateA = a.createdAt || "";
    const dateB = b.createdAt || "";
    return dateB.localeCompare(dateA);
  });

  const handleExportCSV = (estimate: CostEstimate) => {
    if (!estimate.lineItems || estimate.lineItems.length === 0) return;

    const headers = ["Service", "Monthly Quantity", "Unit Price", "Monthly Cost", "Unit"];
    const rows = estimate.lineItems.map((item) => [
      item.name || "",
      String(item.monthlyQuantity || 0),
      String(item.unitPrice || 0),
      String(item.monthlyCost || 0),
      item.unitOfMeasure || "",
    ]);

    const csv = [headers, ...rows].map((row) => row.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `cost-estimate-${estimate.createdAt || "export"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Estimate Selector */}
      {sortedEstimates.length > 1 && (
        <div className="flex gap-2 flex-wrap">
          {sortedEstimates.map((estimate, idx) => {
            const isSelected = selectedEstimate === estimate;
            return (
              <button
                key={estimate.id || idx}
                onClick={() => setSelectedEstimate(estimate)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isSelected
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {estimate.createdAt
                  ? new Date(estimate.createdAt).toLocaleDateString()
                  : `Estimate ${sortedEstimates.length - idx}`}
              </button>
            );
          })}
        </div>
      )}

      {selectedEstimate && (
        <>
          {/* Summary Card */}
          <Card>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle>Cost Estimate</CardTitle>
                  {selectedEstimate.createdAt && (
                    <p className="text-sm text-gray-600 mt-1">
                      Generated: {new Date(selectedEstimate.createdAt).toLocaleString()}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => handleExportCSV(selectedEstimate)}
                  className="flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-sm"
                >
                  <Download className="h-4 w-4" />
                  Export CSV
                </button>
              </div>
            </CardHeader>

            <CardContent>
              <div className="space-y-6">
                {/* Total Cost */}
                <div className="text-center py-6 border-b border-gray-200">
                  <div className="text-5xl font-bold text-gray-900 mb-2">
                    {selectedEstimate.currencyCode || "USD"}{" "}
                    {(selectedEstimate.totalMonthlyCost || 0).toFixed(2)}
                  </div>
                  <div className="text-sm text-gray-600">Per Month</div>
                  {selectedEstimate.variancePct !== undefined && (
                    <Badge
                      variant={selectedEstimate.variancePct > 0 ? "error" : "success"}
                      size="md"
                      className="mt-2"
                    >
                      {selectedEstimate.variancePct > 0 ? "+" : ""}
                      {selectedEstimate.variancePct.toFixed(1)}% variance
                    </Badge>
                  )}
                </div>

                {/* Pie Chart */}
                {selectedEstimate.lineItems && selectedEstimate.lineItems.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900 mb-4">
                      Cost by Service
                    </h3>
                    <CostPieChart lineItems={selectedEstimate.lineItems} />
                  </div>
                )}

                {/* Line Items Table */}
                {selectedEstimate.lineItems && selectedEstimate.lineItems.length > 0 && (
                  <div>
                    <button
                      onClick={() => setExpandedLineItems(!expandedLineItems)}
                      className="flex items-center gap-2 w-full text-left text-sm font-semibold text-gray-900 hover:text-gray-700 transition-colors mb-4"
                    >
                      {expandedLineItems ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                      Line Items ({selectedEstimate.lineItems.length})
                    </button>

                    {expandedLineItems && (
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
                            {selectedEstimate.lineItems.map((item, idx) => (
                              <tr key={item.id || idx} className="hover:bg-gray-50">
                                <td className="px-4 py-3 text-gray-900">
                                  {item.name || "Unknown Service"}
                                </td>
                                <td className="px-4 py-3 text-right text-gray-600">
                                  {item.monthlyQuantity || 0}{" "}
                                  <span className="text-xs text-gray-500">
                                    {item.unitOfMeasure || "units"}
                                  </span>
                                </td>
                                <td className="px-4 py-3 text-right text-gray-600">
                                  {selectedEstimate.currencyCode || "USD"}{" "}
                                  {(item.unitPrice || 0).toFixed(4)}
                                </td>
                                <td className="px-4 py-3 text-right font-medium text-gray-900">
                                  {selectedEstimate.currencyCode || "USD"}{" "}
                                  {(item.monthlyCost || 0).toFixed(2)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}

                {/* Pricing Gaps */}
                {selectedEstimate.pricingGaps && selectedEstimate.pricingGaps.length > 0 && (
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <h4 className="text-sm font-semibold text-amber-900 mb-2">
                          Pricing Gaps ({selectedEstimate.pricingGaps.length})
                        </h4>
                        <div className="space-y-1">
                          {selectedEstimate.pricingGaps.map((gap, idx) => (
                            <div key={idx} className="text-sm text-amber-800">
                              <span className="font-medium">{gap.name || "Unknown"}:</span>{" "}
                              {gap.reason || "Pricing information unavailable"}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
