/**
 * Step Indicator Component
 */

interface Step {
  id: string;
  label: string;
}

interface StepIndicatorProps {
  steps: Step[];
  currentStep: string;
}

export function StepIndicator({ steps, currentStep }: StepIndicatorProps) {
  const currentIndex = steps.findIndex((s) => s.id === currentStep);

  return (
    <div className="flex justify-between items-center">
      {steps.map((step, i) => (
        <div key={step.id} className="flex items-center flex-1">
          <div
            className={`flex items-center justify-center w-8 h-8 rounded-full border-2 ${
              currentStep === step.id
                ? "border-brand bg-brand text-inverse"
                : currentIndex > i
                  ? "border-success bg-success text-inverse"
                  : "border-border-stronger text-dim"
            }`}
          >
            {i + 1}
          </div>
          {i < steps.length - 1 && (
            <div
              className={`flex-1 h-0.5 mx-2 ${
                currentIndex > i ? "bg-success" : "bg-border-stronger"
              }`}
            />
          )}
        </div>
      ))}
    </div>
  );
}




