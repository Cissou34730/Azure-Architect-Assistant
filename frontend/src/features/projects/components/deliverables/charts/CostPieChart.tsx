import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import type { CostLineItem } from "../../../../../types/api";

interface CostPieChartProps {
  readonly lineItems: readonly CostLineItem[];
}

const COLORS = [
  "#0078D4", // Azure Blue
  "#50E6FF", // Light Blue
  "#107C10", // Green
  "#F7630C", // Amber
  "#D13438", // Red
  "#5C2D91", // Purple
  "#00B7C3", // Cyan
  "#767676", // Gray
];

export function CostPieChart({ lineItems }: CostPieChartProps) {
  // Sort by cost and take top 5, group rest as "Others"
  const sortedItems = [...lineItems].sort(
    (a, b) => b.monthlyCost - a.monthlyCost
  );

  const topItems = sortedItems.slice(0, 5);
  const otherItems = sortedItems.slice(5);
  const othersCost = otherItems.reduce((sum, item) => sum + item.monthlyCost, 0);

  const data = topItems.map((item) => ({
    name: item.name,
    value: item.monthlyCost,
  }));

  if (othersCost > 0) {
    data.push({ name: "Others", value: othersCost });
  }

  const formatCurrency = (value: number) => {
    return `$${value.toFixed(2)}`;
  };

  const formatPercentage = (value: number, totalAmount: number) => {
    if (totalAmount === 0) return "0.0%";
    return `${((value / totalAmount) * 100).toFixed(1)}%`;
  };

  const total = data.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="w-full h-80">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({
              name,
              value,
            }: {
              name?: string | number;
              value?: string | number;
            }) => {
              const nameStr = String(name ?? "Unknown");
              const numValue = Number(value ?? 0);
              return `${nameStr}: ${formatPercentage(numValue, total)}`;
            }}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              /* eslint-disable-next-line @typescript-eslint/no-deprecated */
              <Cell
                key={`cell-${entry.name}`}
                fill={COLORS[index % COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number | string | undefined) =>
              formatCurrency(Number(value ?? 0))
            }
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
