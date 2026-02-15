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
                ? "bg-brand text-inverse"
                : "bg-muted text-secondary hover:bg-border"
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
    <div className="text-center py-6 border-b border-border">
      <div className="text-5xl font-bold text-foreground mb-2">
        {estimate.currencyCode} {estimate.totalMonthlyCost.toFixed(2)}
      </div>
      <div className="text-sm text-secondary">Per Month</div>
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
    <tr className="bg-surface divide-x divide-gray-200">
      <th className="px-4 py-3 text-left font-medium text-secondary text-sm">
        Service
      </th>
      <th className="px-4 py-3 text-right font-medium text-secondary text-sm">
        Quantity
      </th>
      <th className="px-4 py-3 text-right font-medium text-secondary text-sm">
        Unit Price
      </th>
      <th className="px-4 py-3 text-right font-medium text-secondary text-sm">
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
        className="flex items-center gap-2 w-full text-left text-sm font-semibold text-foreground hover:text-secondary transition-colors mb-4"
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4" />
        ) : (
          <ChevronRight className="h-4 w-4" />
        )}
        Line Items ({estimate.lineItems.length})
      </button>

      {expanded && (
        <div className="border border-border rounded-lg overflow-hidden">
          {sortedLineItems.length > VIRTUALIZE_THRESHOLD ? (
            <div className="h-96">
              <TableVirtuoso
                data={sortedLineItems}
                fixedHeaderContent={CostLineItemsHeader}
                itemContent={(_index, item) => (
                  <>
                    <td className="px-4 py-3 text-foreground">{item.name}</td>
                    <td className="px-4 py-3 text-right text-secondary">
                      {item.monthlyQuantity}{" "}
                      <span className="text-xs text-dim">
                        {item.unitOfMeasure ?? "units"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-secondary">
                      {estimate.currencyCode} {item.unitPrice.toFixed(4)}
                    </td>
                    <td className="px-4 py-3 text-right font-medium text-foreground">
                      {estimate.currencyCode} {item.monthlyCost.toFixed(2)}
                    </td>
                  </>
                )}
                components={{
                  // eslint-disable-next-line @typescript-eslint/naming-convention -- react-virtuoso requires TableRow key
                  TableRow: (props) => (
                    <tr
                      {...props}
                      className="hover:bg-surface divide-x divide-gray-200"
                    />
                  ),
                }}
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm divide-y divide-gray-200">
                <thead className="bg-surface">
                  <CostLineItemsHeader />
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {sortedLineItems.map((item) => (
                    <tr
                      key={item.id}
                      className="hover:bg-surface divide-x divide-gray-200"
                    >
                      <td className="px-4 py-3 text-foreground">{item.name}</td>
                      <td className="px-4 py-3 text-right text-secondary">
                        {item.monthlyQuantity}{" "}
                        <span className="text-xs text-dim">
                          {item.unitOfMeasure ?? "units"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-secondary">
                        {estimate.currencyCode} {item.unitPrice.toFixed(4)}
                      </td>
                      <td className="px-4 py-3 text-right font-medium text-foreground">
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

interface PricingGap extends Record<string, unknown> {
  readonly name?: string;
  readonly reason?: string;
}

interface PricingGapsProps {
  readonly gaps: readonly PricingGap[];
}

function getPricingGapKey(gap: PricingGap): string {
  const name = typeof gap.name === "string" ? gap.name : "";
  const reason = typeof gap.reason === "string" ? gap.reason : "";
  if (name !== "") return `gap-${name}`;
  if (reason !== "") return `gap-${reason}`;
  return `gap-${JSON.stringify(gap)}`;
}

export function PricingGaps({ gaps }: PricingGapsProps) {
  if (gaps.length === 0) return null;

  return (
    <div className="bg-warning-soft border border-warning-line rounded-lg p-4">
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-warning shrink-0 mt-0.5" />
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-warning-strong mb-2">
            Pricing Gaps ({gaps.length})
          </h4>
          <div className="space-y-1">
            {gaps.map((gap) => (
              <div key={getPricingGapKey(gap)} className="text-sm text-warning-strong">
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
    <div className="w-full h-80 bg-surface animate-pulse rounded-lg flex items-center justify-center">
      <div className="text-dim text-sm">Loading charts...</div>
    </div>
  );
}



