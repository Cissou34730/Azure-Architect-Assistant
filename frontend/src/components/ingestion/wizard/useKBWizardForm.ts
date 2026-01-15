/**
 * Custom hook for KB Wizard form state and logic
 */

import { useState, useCallback } from "react";
import { SourceType, CreateKBRequest } from "../../../types/ingestion";
import { createKB, startIngestion } from "../../../services/ingestionApi";
import { buildSourceConfig } from "../../../utils/ingestionConfig";
import { generateKbId, canProceed as validateStep } from "./wizardUtils";

export type WizardStep = "basic" | "source" | "config" | "review";

function useWebsiteState() {
  const [urls, setUrls] = useState<string[]>([""]);
  const [sitemapUrl, setSitemapUrl] = useState("");
  const [urlPrefix, setUrlPrefix] = useState("");
  return { urls, setUrls, sitemapUrl, setSitemapUrl, urlPrefix, setUrlPrefix };
}

function useYouTubeState() {
  const [videoUrls, setVideoUrls] = useState<string[]>([""]);
  return { videoUrls, setVideoUrls };
}

function usePDFState() {
  const [pdfLocalPaths, setPdfLocalPaths] = useState<string[]>([""]);
  const [pdfUrls, setPdfUrls] = useState<string[]>([""]);
  const [pdfFolderPath, setPdfFolderPath] = useState("");
  return {
    pdfLocalPaths,
    setPdfLocalPaths,
    pdfUrls,
    setPdfUrls,
    pdfFolderPath,
    setPdfFolderPath,
  };
}

interface SubmitParams {
  kbId: string;
  name: string;
  description: string;
  sourceType: SourceType;
  urls: string[];
  sitemapUrl: string;
  urlPrefix: string;
  videoUrls: string[];
  pdfLocalPaths: string[];
  pdfUrls: string[];
  pdfFolderPath: string;
  markdownFolderPath: string;
}

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

function useWizardBaseState() {
  const [step, setStep] = useState<WizardStep>("basic");
  const [kbId, setKbId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [sourceType, setSourceType] = useState<SourceType>("website");

  const handleNameChange = (value: string) => {
    setName(value);
    if (kbId === "" || kbId === generateKbId(name)) {
      setKbId(generateKbId(value));
    }
  };

  return {
    step,
    setStep,
    kbId,
    setKbId,
    name,
    setName: handleNameChange,
    description,
    setDescription,
    sourceType,
    setSourceType,
  };
}

export function useKBWizardForm() {
  const base = useWizardBaseState();
  const web = useWebsiteState();
  const yt = useYouTubeState();
  const pdf = usePDFState();
  const [markdownFolderPath, setMarkdownFolderPath] = useState("");

  const submission = useWizardSubmission({
    kbId: base.kbId,
    name: base.name,
    description: base.description,
    sourceType: base.sourceType,
    urls: web.urls,
    sitemapUrl: web.sitemapUrl,
    urlPrefix: web.urlPrefix,
    videoUrls: yt.videoUrls,
    pdfLocalPaths: pdf.pdfLocalPaths,
    pdfUrls: pdf.pdfUrls,
    pdfFolderPath: pdf.pdfFolderPath,
    markdownFolderPath,
  });

  const canProceed = useCallback(() => {
    return validateStep({
      step: base.step,
      kbId: base.kbId,
      name: base.name,
      sourceType: base.sourceType,
      urls: web.urls,
      sitemapUrl: web.sitemapUrl,
      videoUrls: yt.videoUrls,
      pdfLocalPaths: pdf.pdfLocalPaths,
      pdfUrls: pdf.pdfUrls,
      pdfFolderPath: pdf.pdfFolderPath,
      markdownFolderPath,
    });
  }, [base, web, yt, pdf, markdownFolderPath]);

  return {
    ...base,
    ...submission,
    ...web,
    ...yt,
    ...pdf,
    markdownFolderPath,
    setMarkdownFolderPath,
    canProceed,
  };
}
