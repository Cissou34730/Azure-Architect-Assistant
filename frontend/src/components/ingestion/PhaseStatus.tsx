/* eslint-disable */
import type { PhaseDetail, IngestionPhase } from "../../types/ingestion";

type Props = {
  phases?: readonly PhaseDetail[];
};

const phaseOrder: IngestionPhase[] = [
  "loading",
  "chunking",
  "embedding",
  "indexing",
];

const statusColor: Record<string, string> = {
  not_started: "bg-gray-300",
  pending: "bg-gray-300",
  running: "bg-blue-500",
  paused: "bg-yellow-500",
  completed: "bg-green-500",
  failed: "bg-red-500",
};

export function PhaseStatus({ phases }: Props) {
  const map = new Map<string, PhaseDetail>();
  phases?.forEach((p) => map.set(p.name, p));

  return (
    <div className="grid grid-cols-1 gap-2">
      {phaseOrder.map((name) => {
        const ph = map.get(name);
        const status = ph?.status ?? "not_started";
        const progress = ph?.progress ?? 0;
        const bar = statusColor[status] ?? "bg-gray-300";
        return (
          <div key={name} className="flex flex-col">
            <div className="flex justify-between text-sm">
              <span className="font-medium capitalize">{name}</span>
              <span className="capitalize">{status}</span>
            </div>
            <div className="h-2 bg-gray-200 rounded">
              <div
                className={`h-2 ${bar} rounded`}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default PhaseStatus;
