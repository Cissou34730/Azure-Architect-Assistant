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
  const currentIndex = steps.findIndex(s => s.id === currentStep);

  return (
    <div className="flex justify-between items-center">
      {steps.map((step, i) => (
        <div key={step.id} className="flex items-center flex-1">
          <div className={`flex items-center justify-center w-8 h-8 rounded-full border-2 ${
            currentStep === step.id ? 'border-blue-600 bg-blue-600 text-white' :
            currentIndex > i ? 'border-green-600 bg-green-600 text-white' :
            'border-gray-300 text-gray-400'
          }`}>
            {i + 1}
          </div>
          {i < steps.length - 1 && (
            <div className={`flex-1 h-0.5 mx-2 ${
              currentIndex > i ? 'bg-green-600' : 'bg-gray-300'
            }`} />
          )}
        </div>
      ))}
    </div>
  );
}
