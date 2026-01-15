/**
 * Source Configuration Step Component
 */

import { SourceType } from "../../../types/ingestion";
import { WebsiteConfig } from "./WebsiteConfig";
import { YouTubeConfig } from "./YouTubeConfig";
import { PDFConfig } from "./PDFConfig";
import { MarkdownConfig } from "./MarkdownConfig";

interface ConfigurationStepProps {
  readonly sourceType: SourceType;
  // Website
  readonly urls: string[];
  readonly setUrls: (urls: string[]) => void;
  readonly sitemapUrl: string;
  readonly setSitemapUrl: (url: string) => void;
  readonly urlPrefix: string;
  readonly setUrlPrefix: (prefix: string) => void;
  // YouTube
  readonly videoUrls: string[];
  readonly setVideoUrls: (urls: string[]) => void;
  // PDF
  readonly pdfLocalPaths: string[];
  readonly setPdfLocalPaths: (paths: string[]) => void;
  readonly pdfUrls: string[];
  readonly setPdfUrls: (urls: string[]) => void;
  readonly pdfFolderPath: string;
  readonly setPdfFolderPath: (path: string) => void;
  // Markdown
  readonly markdownFolderPath: string;
  readonly setMarkdownFolderPath: (path: string) => void;
}

export function ConfigurationStep({
  sourceType,
  urls,
  setUrls,
  sitemapUrl,
  setSitemapUrl,
  videoUrls,
  setVideoUrls,
  pdfLocalPaths,
  setPdfLocalPaths,
  pdfUrls,
  setPdfUrls,
  pdfFolderPath,
  setPdfFolderPath,
  markdownFolderPath,
  setMarkdownFolderPath,
  urlPrefix,
  setUrlPrefix,
}: ConfigurationStepProps) {
  const renderConfig = () => {
    switch (sourceType) {
      case "website":
      case "web_documentation":
      case "web_generic":
        return (
          <WebsiteConfig
            urls={urls}
            setUrls={setUrls}
            sitemapUrl={sitemapUrl}
            setSitemapUrl={setSitemapUrl}
            urlPrefix={urlPrefix}
            setUrlPrefix={setUrlPrefix}
          />
        );
      case "youtube":
        return (
          <YouTubeConfig videoUrls={videoUrls} setVideoUrls={setVideoUrls} />
        );
      case "pdf":
        return (
          <PDFConfig
            pdfLocalPaths={pdfLocalPaths}
            setPdfLocalPaths={setPdfLocalPaths}
            pdfUrls={pdfUrls}
            setPdfUrls={setPdfUrls}
            pdfFolderPath={pdfFolderPath}
            setPdfFolderPath={setPdfFolderPath}
          />
        );
      case "markdown":
        return (
          <MarkdownConfig
            markdownFolderPath={markdownFolderPath}
            setMarkdownFolderPath={setMarkdownFolderPath}
          />
        );
      default:
        return (
          <p className="text-gray-500 italic">
            No configuration needed for this source type.
          </p>
        );
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">
        Source Configuration
      </h3>
      {renderConfig()}
    </div>
  );
}
