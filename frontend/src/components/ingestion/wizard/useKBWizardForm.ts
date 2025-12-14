/**
 * Custom hook for KB Wizard form state and logic
 */

import { useState } from "react";
import { 
  SourceType, 
  CreateKBRequest,
  WebsiteSourceConfig,
  YoutubeSourceConfig,
  PDFSourceConfig,
  MarkdownSourceConfig
} from "../../../types/ingestion";
import { createKB, startIngestion } from "../../../services/ingestionApi";

export type WizardStep = "basic" | "source" | "config" | "review";

export function useKBWizardForm() {
  const [step, setStep] = useState<WizardStep>("basic");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [kbId, setKbId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [sourceType, setSourceType] = useState<SourceType>("website");

  // Website config
  const [urls, setUrls] = useState<string[]>([""]);
  const [sitemapUrl, setSitemapUrl] = useState("");
  const [urlPrefix, setUrlPrefix] = useState("");

  // YouTube config
  const [videoUrls, setVideoUrls] = useState<string[]>([""]);

  // PDF config
  const [pdfLocalPaths, setPdfLocalPaths] = useState<string[]>([""]);
  const [pdfUrls, setPdfUrls] = useState<string[]>([""]);
  const [pdfFolderPath, setPdfFolderPath] = useState("");

  // Markdown config
  const [markdownFolderPath, setMarkdownFolderPath] = useState("");

  // Legacy fields (kept for backwards compatibility during transition)
  const [startUrls, setStartUrls] = useState<string[]>([""]);
  const [allowedDomains, setAllowedDomains] = useState<string[]>([""]);
  const [pathPrefix, setPathPrefix] = useState("");
  const [followLinks, setFollowLinks] = useState(true);
  const [maxPages, setMaxPages] = useState(1000);

  const generateKbId = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  };

  const handleNameChange = (value: string) => {
    setName(value);
    if (!kbId || kbId === generateKbId(name)) {
      setKbId(generateKbId(value));
    }
  };

  const handleSubmit = async (onSuccess: (kbId: string) => void) => {
    setLoading(true);
    setError(null);

    try {
      // Build source config based on type
      let sourceConfig: WebsiteSourceConfig | YoutubeSourceConfig | PDFSourceConfig | MarkdownSourceConfig;

      if (sourceType === "website") {
        sourceConfig = sitemapUrl
          ? {
              sitemap_url: sitemapUrl,
              url_prefix: urlPrefix || undefined,
            }
          : {
              start_url: urls[0]?.trim(),
              url_prefix: urlPrefix || undefined,
              max_pages: maxPages || 1000,
            };
      } else if (sourceType === "youtube") {
        sourceConfig = {
          video_urls: videoUrls.filter((url) => url.trim()),
        };
      } else if (sourceType === "pdf") {
        sourceConfig = {
          local_paths: pdfLocalPaths.filter((p) => p.trim()),
          pdf_urls: pdfUrls.filter((url) => url.trim()),
          folder_path: pdfFolderPath || undefined,
        };
        // Remove empty arrays
        if (!sourceConfig.local_paths.length) delete sourceConfig.local_paths;
        if (!sourceConfig.pdf_urls.length) delete sourceConfig.pdf_urls;
      } else {
        // markdown
        sourceConfig = {
          folder_path: markdownFolderPath,
        };
      }

      // Create KB
      const request: CreateKBRequest = {
        kb_id: kbId,
        name,
        description: description || undefined,
        source_type: sourceType,
        source_config: sourceConfig,
        embedding_model: "text-embedding-3-small",
        chunk_size: 1024,
        chunk_overlap: 200,
        profiles: ["chat", "kb-query"],
        priority: 2,
      };

      await createKB(request);

      // Start ingestion
      await startIngestion(kbId);

      onSuccess(kbId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create KB");
    } finally {
      setLoading(false);
    }
  };

  const canProceed = () => {
    switch (step) {
      case "basic":
        return kbId && name;
      case "source":
        return sourceType;
      case "config":
        if (sourceType === "website") {
          return sitemapUrl || urls.some((url) => url.trim());
        } else if (sourceType === "youtube") {
          return videoUrls.some((url) => url.trim());
        } else if (sourceType === "pdf") {
          return (
            pdfLocalPaths.some((p) => p.trim()) ||
            pdfUrls.some((url) => url.trim()) ||
            pdfFolderPath.trim()
          );
        } else if (sourceType === "markdown") {
          return markdownFolderPath.trim();
        }
        return false;
      case "review":
        return true;
      default:
        return false;
    }
  };

  return {
    step,
    setStep,
    loading,
    error,
    setError,
    kbId,
    setKbId,
    name,
    setName: handleNameChange,
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
    // Legacy (kept for backwards compatibility)
    startUrls,
    setStartUrls,
    allowedDomains,
    setAllowedDomains,
    pathPrefix,
    setPathPrefix,
    followLinks,
    setFollowLinks,
    maxPages,
    setMaxPages,
    handleSubmit,
    canProceed,
  };
}
