import { Button } from "../common";
import { KBJobControls } from "./KBJobControls";

interface KBActionsProps {
  readonly kbId: string;
  readonly isIngesting: boolean;
  readonly isPaused: boolean;
  readonly canStartIngestion: boolean;
  readonly onViewProgress: (kbId: string) => void;
  readonly onStartIngestion: (kbId: string) => void;
  readonly onRefresh: () => void;
}

export function KBActions({
  kbId,
  isIngesting,
  isPaused,
  canStartIngestion,
  onViewProgress,
  onStartIngestion,
  onRefresh,
}: KBActionsProps) {
  if (isIngesting || isPaused) {
    return (
      <>
        <Button
          variant="primary"
          size="sm"
          onClick={() => {
            onViewProgress(kbId);
          }}
        >
          View Progress
        </Button>
        <KBJobControls
          kbId={kbId}
          isRunning={isIngesting}
          isPaused={isPaused}
          onRefresh={onRefresh}
          onViewProgress={onViewProgress}
        />
      </>
    );
  }

  if (canStartIngestion) {
    return (
      <Button
        variant="success"
        size="sm"
        onClick={() => {
          onStartIngestion(kbId);
        }}
      >
        Start Ingestion
      </Button>
    );
  }

  return null;
}
