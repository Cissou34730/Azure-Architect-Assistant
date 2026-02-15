import { WizardStep } from "./useKBWizardForm";

interface WizardFooterProps {
  readonly step: WizardStep;
  readonly loading: boolean;
  readonly canProceed: () => boolean;
  readonly onCancel: () => void;
  readonly onBack: () => void;
  readonly onNext: () => void;
  readonly onSubmit: () => void;
}

export function WizardFooter({
  step,
  loading,
  canProceed,
  onCancel,
  onBack,
  onNext,
  onSubmit,
}: WizardFooterProps) {
  return (
    <div className="px-6 py-4 border-t flex justify-between">
      <button
        onClick={onCancel}
        className="px-4 py-2 text-secondary hover:bg-muted rounded-md"
        disabled={loading}
      >
        Cancel
      </button>

      <div className="flex gap-2">
        {step !== "basic" && (
          <button
            onClick={onBack}
            className="px-4 py-2 text-secondary hover:bg-muted rounded-md"
            disabled={loading}
          >
            Back
          </button>
        )}

        {step !== "review" ? (
          <button
            onClick={onNext}
            disabled={!canProceed() || loading}
            className="px-4 py-2 bg-brand text-inverse rounded-md hover:bg-brand-strong disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        ) : (
          <button
            onClick={onSubmit}
            disabled={loading}
            className="px-4 py-2 bg-success text-inverse rounded-md hover:bg-success-strong disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Creating..." : "Create KB"}
          </button>
        )}
      </div>
    </div>
  );
}



