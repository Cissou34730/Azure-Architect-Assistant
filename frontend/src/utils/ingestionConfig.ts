import {
  SourceType,
  WebsiteSourceConfig,
  YoutubeSourceConfig,
  PDFSourceConfig,
  MarkdownSourceConfig,
} from "../types/ingestion";

export interface ConfigInputs {
  sourceType: SourceType;
  // Website
  urls: string[];
  urlPrefix: string;
  maxPages: number;
  // YouTube
  videoUrls: string[];
  // PDF
  pdfLocalPaths: string[];
  pdfUrls: string[];
  pdfFolderPath: string;
  // Markdown
  markdownFolderPath: string;
}

function buildWebsiteConfig(inputs: ConfigInputs): WebsiteSourceConfig {
  const { urlPrefix, urls, maxPages } = inputs;
  return {
    startUrl: urls[0]?.trim() ?? "",
    urlPrefix: urlPrefix !== "" ? urlPrefix : undefined,
    maxPages: maxPages !== 0 ? maxPages : 1000,
  };
}

function buildPDFConfig(inputs: ConfigInputs): PDFSourceConfig {
  const { pdfLocalPaths, pdfUrls, pdfFolderPath } = inputs;
  const localPaths = pdfLocalPaths.filter((path) => path.trim() !== "");
  const filteredPdfUrls = pdfUrls.filter((url) => url.trim() !== "");

  return {
    localPaths: localPaths.length > 0 ? localPaths : undefined,
    pdfUrls: filteredPdfUrls.length > 0 ? filteredPdfUrls : undefined,
    folderPath: pdfFolderPath !== "" ? pdfFolderPath : undefined,
  };
}

export function buildSourceConfig(
  inputs: ConfigInputs
):
  | WebsiteSourceConfig
  | YoutubeSourceConfig
  | PDFSourceConfig
  | MarkdownSourceConfig {
  const { sourceType, videoUrls, markdownFolderPath } = inputs;

  if (sourceType === "website") {
    return buildWebsiteConfig(inputs);
  }

  if (sourceType === "youtube") {
    return {
      videoUrls: videoUrls.filter((url) => url.trim() !== ""),
    };
  }

  if (sourceType === "pdf") {
    return buildPDFConfig(inputs);
  }

  return {
    folderPath: markdownFolderPath,
  };
}
