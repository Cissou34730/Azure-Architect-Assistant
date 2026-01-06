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
  sitemapUrl: string;
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

export function buildSourceConfig(
  inputs: ConfigInputs
):
  | WebsiteSourceConfig
  | YoutubeSourceConfig
  | PDFSourceConfig
  | MarkdownSourceConfig {
  const {
    sourceType,
    urls,
    sitemapUrl,
    urlPrefix,
    maxPages,
    videoUrls,
    pdfLocalPaths,
    pdfUrls,
    pdfFolderPath,
    markdownFolderPath,
  } = inputs;

  if (sourceType === "website") {
    return sitemapUrl
      ? {
          sitemap_url: sitemapUrl,
          url_prefix: urlPrefix || undefined,
        }
      : {
          start_url: urls[0]?.trim(),
          url_prefix: urlPrefix || undefined,
          max_pages: maxPages || 1000,
        };
  }

  if (sourceType === "youtube") {
    return {
      video_urls: videoUrls.filter((url) => url.trim()),
    };
  }

  if (sourceType === "pdf") {
    const config: PDFSourceConfig = {
      local_paths: pdfLocalPaths.filter((p) => p.trim()),
      pdf_urls: pdfUrls.filter((url) => url.trim()),
      folder_path: pdfFolderPath || undefined,
    };
    // Clean empty arrays to match backend expectations
    if (!config.local_paths?.length) delete config.local_paths;
    if (!config.pdf_urls?.length) delete config.pdf_urls;
    return config;
  }

  // Markdown
  return {
    folder_path: markdownFolderPath,
  };
}
