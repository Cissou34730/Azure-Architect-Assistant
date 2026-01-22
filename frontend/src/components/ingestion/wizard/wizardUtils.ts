/**
 * Utility functions for the KB Creation Wizard
 */

import { SourceType } from "../../../types/ingestion";
import { WizardStep } from "./useKBWizardForm";

/**
 * Generates a URL-safe KB ID from a name
 */
export function generateKbId(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

interface ValidationData {
  step: WizardStep;
  kbId: string;
  name: string;
  sourceType: SourceType;
  urls: string[];
  videoUrls: string[];
  pdfLocalPaths: string[];
  pdfUrls: string[];
  pdfFolderPath: string;
  markdownFolderPath: string;
}

function isHttpUrl(value: string): boolean {
  const trimmed = value.trim();
  if (trimmed === "") {
    return false;
  }

  try {
    const parsed = new URL(trimmed);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

/**
 * Validates if the user can proceed to the next step
 */
export function canProceed(data: ValidationData): boolean {
  switch (data.step) {
    case "basic":
      return data.kbId.trim() !== "" && data.name.trim() !== "";
    case "source":
      return true;
    case "config":
      return validateConfig(data);
    case "review":
      return true;
    default:
      return false;
  }
}

function validateConfig(data: ValidationData): boolean {
  if (
    data.sourceType === "website" ||
    data.sourceType === "web_documentation" ||
    data.sourceType === "web_generic"
  ) {
    return data.urls.some((url) => isHttpUrl(url));
  }
  if (data.sourceType === "youtube") {
    return data.videoUrls.some((url) => url.trim() !== "");
  }
  if (data.sourceType === "pdf") {
    return (
      data.pdfLocalPaths.some((p) => p.trim() !== "") ||
      data.pdfUrls.some((url) => url.trim() !== "") ||
      data.pdfFolderPath.trim() !== ""
    );
  }
  if (data.sourceType === "markdown") {
    return data.markdownFolderPath.trim() !== "";
  }
  return false;
}
