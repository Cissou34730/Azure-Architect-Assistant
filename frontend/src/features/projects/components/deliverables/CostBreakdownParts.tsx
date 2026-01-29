import { useMemo } from "react";
import { ChevronDown, ChevronRight, AlertTriangle } from "lucide-react";
import { TableVirtuoso } from "react-virtuoso";
import { Badge } from "../../../../components/common";
import type { CostEstimate } from "../../../../types/api";

const VIRTUALIZE_THRESHOLD = 20;

interface EstimateSelectorProps {
  readonly estimates: readonly CostEstimate[];
  readonly selectedId: string | undefined;
  readonly onSelect: (estimate: CostEstimate) => void;
}

export function EstimateSelector({
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

interface TotalCostDisplayProps {
  readonly estimate: CostEstimate;
}

export function TotalCostDisplay({ estimate }: TotalCostDisplayProps) {
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

function CostLineItemsHeader() {
  return (
    <tr className="bg-gray-50 divide-x divide-gray-200">
      <th className="px-4 py-3 text-left font-medium text-gray-600 text-sm">
        Service
      </th>
      <th className="px-4 py-3 text-right font-medium text-gray-600 text-sm">
        Quantity
      </th>
      <th className="px-4 py-3 text-right font-medium text-gray-600 text-sm">
        Unit Price
      </th>
      <th className="px-4 py-3 text-right font-medium text-gray-600 text-sm">
        Monthly Cost
      </th>
    </tr>
  );
}

export function LineItemsTable({
  estimate,
  expanded,
  onToggle,
}: LineItemsTableProps) {
  const sortedLineItems = useMemo(() => {
    return [...estimate.lineItems].sort(
      (a, b) => b.monthlyCost - a.monthlyCost,
    );
  }, [estimate.lineItems]);

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
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          {sortedLineItems.length > VIRTUALIZE_THRESHOLD ? (
            <div className="h-96">
              <TableVirtuoso
                data={sortedLineItems}
                fixedHeaderContent={CostLineItemsHeader}
                itemContent={(_index, item) => (
                  <>
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
                  </>
                )}
                components={{
                  // eslint-disable-next-line @typescript-eslint/naming-convention -- react-virtuoso requires TableRow key
                  TableRow: (props) => (
                    <tr
                      {...props}
                      className="hover:bg-gray-50 divide-x divide-gray-200"
                    />
                  ),
                }}
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <CostLineItemsHeader />
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {sortedLineItems.map((item) => (
                    <tr
                      key={item.id}
                      className="hover:bg-gray-50 divide-x divide-gray-200"
                    >
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
      )}
    </div>
  );
}

interface PricingGapsProps {
  // eslint-disable-next-line @typescript-eslint/no-restricted-types -- Backend returns dynamic pricing gap structure
  readonly gaps: readonly Record<string, unknown>[];
}

export function PricingGaps({ gaps }: PricingGapsProps) {
  if (gaps.length === 0) return null;

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-amber-900 mb-2">
            Pricing Gaps ({gaps.length})
          </h4>
          <div className="space-y-1">
            {/* eslint-disable-next-line react/no-array-index-key -- Gap objects have no stable ID */}
            {gaps.map((gap, idx) => (
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

export function ChartSkeleton() {
  return (
    <div className="w-full h-80 bg-gray-50 animate-pulse rounded-lg flex items-center justify-center">
      <div className="text-gray-400 text-sm">Loading charts...</div>
    </div>
  );
}
