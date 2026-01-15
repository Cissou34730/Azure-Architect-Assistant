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
        className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-md"
        disabled={loading}
      >
        Cancel
      </button>

      <div className="flex gap-2">
        {step !== "basic" && (
          <button
            onClick={onBack}
            className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-md"
            disabled={loading}
          >
            Back
          </button>
        )}

        {step !== "review" ? (
          <button
            onClick={onNext}
            disabled={!canProceed() || loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        ) : (
          <button
            onClick={onSubmit}
            disabled={loading}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Creating..." : "Create KB"}
          </button>
        )}
      </div>
    </div>
  );
}
