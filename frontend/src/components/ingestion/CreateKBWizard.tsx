/**
 * Create KB Wizard Component
 * Multi-step wizard for creating a new knowledge base
 */

import { useKBWizardForm, WizardStep } from "./wizard/useKBWizardForm";
import { StepIndicator } from "./wizard/StepIndicator";
import { WizardContent } from "./wizard/WizardContent";
import { WizardFooter } from "./wizard/WizardFooter";

interface CreateKBWizardProps {
  readonly onSuccess: (kbId: string) => void;
  readonly onCancel: () => void;
}

const WIZARD_STEPS = [
  { id: "basic", label: "Basic Info" },
  { id: "source", label: "Source Type" },
  { id: "config", label: "Configuration" },
  { id: "review", label: "Review" },
];

export function CreateKBWizard({ onSuccess, onCancel }: CreateKBWizardProps) {
  const form = useKBWizardForm();
  const { step, setStep, loading, error, handleSubmit, canProceed } = form;

  const handleNext = () => {
    const steps: WizardStep[] = ["basic", "source", "config", "review"];
    const currentIndex = steps.indexOf(step);
    if (currentIndex < steps.length - 1) {
      setStep(steps[currentIndex + 1]);
    }
  };

  const handleBack = () => {
    const steps: WizardStep[] = ["basic", "source", "config", "review"];
    const currentIndex = steps.indexOf(step);
    if (currentIndex > 0) {
      setStep(steps[currentIndex - 1]);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg max-w-3xl mx-auto">
      <div className="px-6 py-4 border-b">
        <h2 className="text-2xl font-bold text-gray-900">
          Create Knowledge Base
        </h2>
        <div className="mt-4">
          <StepIndicator steps={WIZARD_STEPS} currentStep={step} />
        </div>
      </div>

      <div className="px-6 py-6 min-h-100">
        {error !== null && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <div className="text-sm text-red-600">{error}</div>
          </div>
        )}
        <WizardContent form={form} />
      </div>

      <WizardFooter
        step={step}
        loading={loading}
        canProceed={canProceed}
        onCancel={onCancel}
        onBack={handleBack}
        onNext={handleNext}
        onSubmit={() => { void handleSubmit(onSuccess); }}
      />
    </div>
  );
}
