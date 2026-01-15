/**
 * Custom hook for KB Wizard form state and logic
 */

import { useState } from "react";
import { SourceType, CreateKBRequest } from "../../../types/ingestion";
import { createKB, startIngestion } from "../../../services/ingestionApi";
import { buildSourceConfig } from "../../../utils/ingestionConfig";
import {
  SourceInputValues,
  SubmitParams,
  useKBWizardState,
  useMarkdownInputs,
  usePDFInputs,
  useSourceInputValues,
  useValidationPayload,
  useWizardValidation,
  useWebsiteInputs,
  useYouTubeInputs,
} from "./useKBWizardForm.helpers";

export type { WizardStep } from "./useKBWizardForm.helpers";

async function performSubmission(
  params: SubmitParams,
  onSuccess: (kbId: string) => void
) {
  const sourceConfig = buildSourceConfig({
    sourceType: params.sourceType,
    urls: params.urls,
    sitemapUrl: params.sitemapUrl,
    urlPrefix: params.urlPrefix,
    maxPages: 1000,
    videoUrls: params.videoUrls,
    pdfLocalPaths: params.pdfLocalPaths,
    pdfUrls: params.pdfUrls,
    pdfFolderPath: params.pdfFolderPath,
    markdownFolderPath: params.markdownFolderPath,
  });

  const request: CreateKBRequest = {
    kbId: params.kbId,
    name: params.name,
    description: params.description !== "" ? params.description : undefined,
    sourceType: params.sourceType,
    sourceConfig,
    embeddingModel: "text-embedding-3-small",
    chunkSize: 1024,
    chunkOverlap: 200,
    profiles: ["chat", "kb-query"],
    priority: 2,
  };

  await createKB(request);
  await startIngestion(params.kbId);
  onSuccess(params.kbId);
}

function useWizardSubmission(params: SubmitParams) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (onSuccess: (kbId: string) => void) => {
    setLoading(true);
    setError(null);
    try {
      await performSubmission(params, onSuccess);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create KB");
    } finally {
      setLoading(false);
    }
  };

  return { loading, error, setError, handleSubmit };
}

function buildSubmitParams({
  kbId,
  name,
  description,
  sourceType,
  sourceInputs,
}: {
  kbId: string;
  name: string;
  description: string;
  sourceType: SourceType;
  sourceInputs: SourceInputValues;
}): SubmitParams {
  return {
    kbId,
    name,
    description,
    sourceType,
    urls: sourceInputs.urls,
    sitemapUrl: sourceInputs.sitemapUrl,
    urlPrefix: sourceInputs.urlPrefix,
    videoUrls: sourceInputs.videoUrls,
    pdfLocalPaths: sourceInputs.pdfLocalPaths,
    pdfUrls: sourceInputs.pdfUrls,
    pdfFolderPath: sourceInputs.pdfFolderPath,
    markdownFolderPath: sourceInputs.markdownFolderPath,
  };
}

interface WizardDerivedStateArgs {
  formState: ReturnType<typeof useKBWizardState>;
  websiteInputs: ReturnType<typeof useWebsiteInputs>;
  youtubeInputs: ReturnType<typeof useYouTubeInputs>;
  pdfInputs: ReturnType<typeof usePDFInputs>;
  markdownInputs: ReturnType<typeof useMarkdownInputs>;
}

function useWizardFormDerivedState({
  formState,
  websiteInputs,
  youtubeInputs,
  pdfInputs,
  markdownInputs,
}: WizardDerivedStateArgs) {
  const { step, kbId, name, description, sourceType } = formState;

  const sourceInputValues = useSourceInputValues({
    websiteInputs,
    youtubeInputs,
    pdfInputs,
    markdownInputs,
  });

  const submissionParams = buildSubmitParams({
    kbId,
    name,
    description,
    sourceType,
    sourceInputs: sourceInputValues,
  });

  const submission = useWizardSubmission(submissionParams);

  const validationPayload = useValidationPayload({
    step,
    kbId,
    name,
    sourceType,
    sourceInputValues,
  });

  const canProceed = useWizardValidation(validationPayload);

  return { submission, canProceed };
}

export function useKBWizardForm() {
  const formState = useKBWizardState();

  const websiteInputs = useWebsiteInputs();
  const youtubeInputs = useYouTubeInputs();
  const pdfInputs = usePDFInputs();
  const markdownInputs = useMarkdownInputs();

  const { submission, canProceed } = useWizardFormDerivedState({
    formState,
    websiteInputs,
    youtubeInputs,
    pdfInputs,
    markdownInputs,
  });

  return {
    ...formState,
    ...submission,
    ...websiteInputs,
    ...youtubeInputs,
    ...pdfInputs,
    ...markdownInputs,
    canProceed,
  };
}
