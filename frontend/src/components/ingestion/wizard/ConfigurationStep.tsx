/**
 * Source Configuration Step Component
 */

import { SourceType } from "../../../types/ingestion";
import { ArrayInput } from "./ArrayInput";

interface ConfigurationStepProps {
  sourceType: SourceType;
  // Website
  urls: string[];
  setUrls: (urls: string[]) => void;
  sitemapUrl: string;
  setSitemapUrl: (url: string) => void;
  urlPrefix: string;
  setUrlPrefix: (prefix: string) => void;
  // YouTube
  videoUrls: string[];
  setVideoUrls: (urls: string[]) => void;
  // PDF
  pdfLocalPaths: string[];
  setPdfLocalPaths: (paths: string[]) => void;
  pdfUrls: string[];
  setPdfUrls: (urls: string[]) => void;
  pdfFolderPath: string;
  setPdfFolderPath: (path: string) => void;
  // Markdown
  markdownFolderPath: string;
  setMarkdownFolderPath: (path: string) => void;
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
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">
        Source Configuration
      </h3>

      {sourceType === "website" && (
        <>
          <div>
            <label
              htmlFor="sitemap-url"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Sitemap URL (Optional)
            </label>
            <input
              id="sitemap-url"
              type="text"
              value={sitemapUrl}
              onChange={(e) => { setSitemapUrl(e.target.value); }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="https://example.com/sitemap.xml"
            />
            <p className="mt-1 text-xs text-gray-500">
              Provide sitemap URL to automatically crawl all pages, or specify
              individual URLs below
            </p>
          </div>

          {sitemapUrl && (
            <div>
              <label
                htmlFor="url-prefix"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                URL Prefix Filter (Recommended)
              </label>
              <input
                id="url-prefix"
                type="text"
                value={urlPrefix}
                onChange={(e) => { setUrlPrefix(e.target.value); }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="https://example.com/docs/section/"
              />
              <p className="mt-1 text-xs text-gray-500">
                Only ingest URLs starting with this prefix. Prevents crawling
                the entire site.
              </p>
            </div>
          )}

          {!sitemapUrl && (
            <ArrayInput
              label="URLs *"
              values={urls}
              onChange={setUrls}
              placeholder="https://example.com/page"
              helpText="Specific web pages to crawl (required if no sitemap provided)"
            />
          )}
        </>
      )}

      {sourceType === "youtube" && (
        <>
          <ArrayInput
            label="Video URLs *"
            values={videoUrls}
            onChange={setVideoUrls}
            placeholder="https://www.youtube.com/watch?v=..."
            helpText="YouTube video URLs to extract and distill transcripts from"
          />
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
            <p className="text-sm text-blue-800">
              💡 Transcripts will be automatically distilled using LLM to
              extract key concepts and technical Q&A
            </p>
          </div>
        </>
      )}

      {sourceType === "pdf" && (
        <>
          <ArrayInput
            label="Local PDF Paths"
            values={pdfLocalPaths}
            onChange={setPdfLocalPaths}
            placeholder="C:\Documents\file.pdf"
            helpText="Absolute paths to PDF files on your computer"
          />

          <ArrayInput
            label="Online PDF URLs"
            values={pdfUrls}
            onChange={setPdfUrls}
            placeholder="https://example.com/document.pdf"
            helpText="Direct URLs to PDF files"
          />

          <div>
            <label
              htmlFor="pdf-folder"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              PDF Folder Path
            </label>
            <input
              id="pdf-folder"
              type="text"
              value={pdfFolderPath}
              onChange={(e) => { setPdfFolderPath(e.target.value); }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="C:\Documents\PDFs"
            />
            <p className="mt-1 text-xs text-gray-500">
              Process all PDF files in this folder
            </p>
          </div>

          <div className="p-3 bg-amber-50 border border-amber-200 rounded-md">
            <p className="text-sm text-amber-800">
              ⚠️ At least one PDF source (local path, URL, or folder) is
              required
            </p>
          </div>
        </>
      )}

      {sourceType === "markdown" && (
        <>
          <div>
            <label
              htmlFor="markdown-folder"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Markdown Folder Path *
            </label>
            <input
              id="markdown-folder"
              type="text"
              value={markdownFolderPath}
              onChange={(e) => { setMarkdownFolderPath(e.target.value); }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="C:\Documentation\markdown"
            />
            <p className="mt-1 text-xs text-gray-500">
              Path to folder containing .md files (will recursively process
              subfolders)
            </p>
          </div>

          <div className="p-3 bg-green-50 border border-green-200 rounded-md">
            <p className="text-sm text-green-800">
              ✅ Markdown structure and hierarchy will be preserved in metadata
            </p>
          </div>
        </>
      )}
    </div>
  );
}
