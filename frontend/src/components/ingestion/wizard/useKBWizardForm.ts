/**
 * Custom hook for KB Wizard form state and logic
 */

import { useState } from "react";
import {
  SourceType,
  CreateKBRequest,
  WebDocumentationConfig,
  WebGenericConfig,
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
  const [sourceType, setSourceType] = useState<SourceType>("web_documentation");
  const [startUrls, setStartUrls] = useState<string[]>([""]);
  const [allowedDomains, setAllowedDomains] = useState<string[]>([""]);
  const [pathPrefix, setPathPrefix] = useState("");
  const [followLinks, setFollowLinks] = useState(true);
  const [maxPages, setMaxPages] = useState(1000);
  const [urls, setUrls] = useState<string[]>([""]);

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
      let sourceConfig: WebDocumentationConfig | WebGenericConfig;

      if (sourceType === "web_documentation") {
        sourceConfig = {
          start_urls: startUrls.filter((url) => url.trim()),
          allowed_domains: allowedDomains.filter((d) => d.trim()),
          path_prefix: pathPrefix || undefined,
          follow_links: followLinks,
          max_pages: maxPages,
        };
      } else {
        sourceConfig = {
          urls: urls.filter((url) => url.trim()),
          follow_links: followLinks,
          max_depth: 1,
          same_domain_only: true,
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
        chunk_size: 800,
        chunk_overlap: 120,
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
        if (sourceType === "web_documentation") {
          return startUrls.some((url) => url.trim());
        }
        return urls.some((url) => url.trim());
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
    urls,
    setUrls,
    handleSubmit,
    canProceed,
  };
}
