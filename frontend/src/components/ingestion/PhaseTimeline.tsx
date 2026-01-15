import { IngestionJob, IngestionPhase } from "../../types/ingestion";

const PHASE_ORDER: IngestionPhase[] = [
  "loading",
  "chunking",
  "embedding",
  "indexing",
  "completed",
];

const PHASE_LABELS: Record<string, string> = {
  loading: "Loading",
  chunking: "Chunking",
  embedding: "Embedding",
  indexing: "Indexing",
  completed: "Finished",
};

const PHASE_COLORS: Record<string, string> = {
  loading: "bg-blue-500",
  chunking: "bg-indigo-500",
  embedding: "bg-purple-500",
  indexing: "bg-pink-500",
  completed: "bg-green-500",
};

interface PhaseIndicatorProps {
  readonly phase: IngestionPhase;
  readonly index: number;
  readonly isComplete: boolean;
  readonly isActive: boolean;
}

function PhaseIndicator({
  phase,
  index,
  isComplete,
  isActive,
}: PhaseIndicatorProps) {
  const getIcon = () => {
    if (isComplete) {
      return (
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 13l4 4L19 7"
          />
        </svg>
      );
    }
    return <span className="text-sm font-semibold">{index + 1}</span>;
  };

  const getContainerClass = () => {
    if (isComplete) {
      return "bg-green-500 text-white";
    }
    if (isActive) {
      return `${PHASE_COLORS[phase] ?? "bg-blue-500"} text-white animate-pulse`;
    }
    return "bg-gray-200 text-gray-400";
  };

  const getLabelClass = () => {
    if (isActive) {
      return "text-gray-900";
    }
    if (isComplete) {
      return "text-gray-700";
    }
    return "text-gray-400";
  };

  return (
    <div key={phase} className="flex items-start gap-3">
      <div className="flex flex-col items-center">
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${getContainerClass()}`}
        >
          {getIcon()}
        </div>
        {index < PHASE_ORDER.length - 1 && (
          <div
            className={`w-0.5 h-6 my-1 ${
              isComplete ? "bg-green-500" : "bg-gray-200"
            }`}
          />
        )}
      </div>

      <div className="flex-1 pt-1">
        <div className="flex justify-between items-center">
          <span className={`text-sm font-medium ${getLabelClass()}`}>
            {PHASE_LABELS[phase] ?? phase}
          </span>
          {isActive && (
            <span className="text-xs font-bold text-blue-600 animate-pulse">
              PROCESSING...
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export function PhaseTimeline({ job }: { readonly job: IngestionJob }) {
  const isRunning = job.status === "running" || job.status === "pending";
  const currentPhaseIndex = PHASE_ORDER.indexOf(job.phase);

  const isComplete = (phase: IngestionPhase) => {
    if (job.status === "completed") return true;
    if (job.status === "failed") return false;
    const phaseIndex = PHASE_ORDER.indexOf(phase);
    return phaseIndex < currentPhaseIndex;
  };

  const isActive = (phase: IngestionPhase) => phase === job.phase && isRunning;

  return (
    <div className="space-y-3">
      {PHASE_ORDER.map((phase, index) => (
        <PhaseIndicator
          key={phase}
          phase={phase}
          index={index}
          isComplete={isComplete(phase)}
          isActive={isActive(phase)}
        />
      ))}
    </div>
  );
}
