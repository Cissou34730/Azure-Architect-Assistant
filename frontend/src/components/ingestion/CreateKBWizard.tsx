/**
 * Create KB Wizard Component
 * Multi-step wizard for creating a new knowledge base
 */

import { useKBWizardForm, WizardStep } from './wizard/useKBWizardForm';
import { StepIndicator } from './wizard/StepIndicator';
import { BasicInfoStep } from './wizard/BasicInfoStep';
import { SourceTypeStep } from './wizard/SourceTypeStep';
import { ConfigurationStep } from './wizard/ConfigurationStep';
import { ReviewStep } from './wizard/ReviewStep';

interface CreateKBWizardProps {
  onSuccess: (kbId: string) => void;
  onCancel: () => void;
}

const WIZARD_STEPS = [
  { id: 'basic', label: 'Basic Info' },
  { id: 'source', label: 'Source Type' },
  { id: 'config', label: 'Configuration' },
  { id: 'review', label: 'Review' },
];

export function CreateKBWizard({ onSuccess, onCancel }: CreateKBWizardProps) {
  const form = useKBWizardForm();
  const {
    step,
    setStep,
    loading,
    error,
    kbId,
    setKbId,
    name,
    setName,
    description,
    setDescription,
    sourceType,
    setSourceType,
    // Website
    urls,
    setUrls,
    sitemapUrl,
    setSitemapUrl,
    urlPrefix,
    setUrlPrefix,
    // YouTube
    videoUrls,
    setVideoUrls,
    // PDF
    pdfLocalPaths,
    setPdfLocalPaths,
    pdfUrls,
    setPdfUrls,
    pdfFolderPath,
    setPdfFolderPath,
    // Markdown
    markdownFolderPath,
    setMarkdownFolderPath,
    handleSubmit,
    canProceed,
  } = form;

  const handleNext = () => {
    const steps: WizardStep[] = ['basic', 'source', 'config', 'review'];
    const currentIndex = steps.indexOf(step);
    if (currentIndex < steps.length - 1) {
      setStep(steps[currentIndex + 1]);
    }
  };

  const handleBack = () => {
    const steps: WizardStep[] = ['basic', 'source', 'config', 'review'];
    const currentIndex = steps.indexOf(step);
    if (currentIndex > 0) {
      setStep(steps[currentIndex - 1]);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg max-w-3xl mx-auto">
      {/* Header */}
      <div className="px-6 py-4 border-b">
        <h2 className="text-2xl font-bold text-gray-900">Create Knowledge Base</h2>
        <div className="mt-4">
          <StepIndicator steps={WIZARD_STEPS} currentStep={step} />
        </div>
      </div>

      {/* Content */}
      <div className="px-6 py-6 min-h-[400px]">
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <div className="text-sm text-red-600">{error}</div>
          </div>
        )}

        {step === 'basic' && (
          <BasicInfoStep
            name={name}
            setName={setName}
            kbId={kbId}
            setKbId={setKbId}
            description={description}
            setDescription={setDescription}
          />
        )}

        {step === 'source' && (
          <SourceTypeStep
            sourceType={sourceType}
            setSourceType={setSourceType}
          />
        )}

        {step === 'config' && (
          <ConfigurationStep
            sourceType={sourceType}
            urls={urls}
            setUrls={setUrls}
            sitemapUrl={sitemapUrl}
            setSitemapUrl={setSitemapUrl}
            urlPrefix={urlPrefix}
            setUrlPrefix={setUrlPrefix}
            videoUrls={videoUrls}
            setVideoUrls={setVideoUrls}
            pdfLocalPaths={pdfLocalPaths}
            setPdfLocalPaths={setPdfLocalPaths}
            pdfUrls={pdfUrls}
            setPdfUrls={setPdfUrls}
            pdfFolderPath={pdfFolderPath}
            setPdfFolderPath={setPdfFolderPath}
            markdownFolderPath={markdownFolderPath}
            setMarkdownFolderPath={setMarkdownFolderPath}
          />
        )}

        {step === 'review' && (
          <ReviewStep
            name={name}
            kbId={kbId}
            description={description}
            sourceType={sourceType}
            urls={urls}
            sitemapUrl={sitemapUrl}
            videoUrls={videoUrls}
            pdfLocalPaths={pdfLocalPaths}
            pdfUrls={pdfUrls}
            pdfFolderPath={pdfFolderPath}
            markdownFolderPath={markdownFolderPath}
          />
        )}
      </div>

      {/* Footer */}
      <div className="px-6 py-4 border-t flex justify-between">
        <button
          onClick={onCancel}
          className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-md"
          disabled={loading}
        >
          Cancel
        </button>

        <div className="flex gap-2">
          {step !== 'basic' && (
            <button
              onClick={handleBack}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-md"
              disabled={loading}
            >
              Back
            </button>
          )}

          {step !== 'review' ? (
            <button
              onClick={handleNext}
              disabled={!canProceed() || loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          ) : (
            <button
              onClick={() => handleSubmit(onSuccess)}
              disabled={loading}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating...' : 'Create KB'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
