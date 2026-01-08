/**
 * Source Type Selection Step Component
 */

import { SourceType } from "../../../types/ingestion";

interface SourceTypeStepProps {
  sourceType: SourceType;
  setSourceType: (type: SourceType) => void;
}

export function SourceTypeStep({
  sourceType,
  setSourceType,
}: SourceTypeStepProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Source Type</h3>

      <div className="space-y-3">
        <label
          className={`flex items-start p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors ${
            sourceType === "website" ? "border-blue-600" : "border-gray-200"
          }`}
        >
          <input
            type="radio"
            value="website"
            checked={sourceType === "website"}
            onChange={(e) => setSourceType(e.target.value as SourceType)}
            className="mt-1"
          />
          <div className="ml-3">
            <div className="font-medium text-gray-900">📄 Website</div>
            <div className="text-sm text-gray-600">
              Crawl websites and documentation using Trafilatura (URLs or
              sitemap)
            </div>
          </div>
        </label>

        <label
          className={`flex items-start p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors ${
            sourceType === "youtube" ? "border-blue-600" : "border-gray-200"
          }`}
        >
          <input
            type="radio"
            value="youtube"
            checked={sourceType === "youtube"}
            onChange={(e) => setSourceType(e.target.value as SourceType)}
            className="mt-1"
          />
          <div className="ml-3">
            <div className="font-medium text-gray-900">🎥 YouTube</div>
            <div className="text-sm text-gray-600">
              Extract and distill transcripts from YouTube videos with LLM
            </div>
          </div>
        </label>

        <label
          className={`flex items-start p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors ${
            sourceType === "pdf" ? "border-blue-600" : "border-gray-200"
          }`}
        >
          <input
            type="radio"
            value="pdf"
            checked={sourceType === "pdf"}
            onChange={(e) => setSourceType(e.target.value as SourceType)}
            className="mt-1"
          />
          <div className="ml-3">
            <div className="font-medium text-gray-900">📑 PDF Files</div>
            <div className="text-sm text-gray-600">
              Upload local PDFs or provide URLs to online PDF documents
            </div>
          </div>
        </label>

        <label
          className={`flex items-start p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors ${
            sourceType === "markdown" ? "border-blue-600" : "border-gray-200"
          }`}
        >
          <input
            type="radio"
            value="markdown"
            checked={sourceType === "markdown"}
            onChange={(e) => setSourceType(e.target.value as SourceType)}
            className="mt-1"
          />
          <div className="ml-3">
            <div className="font-medium text-gray-900">📝 Markdown</div>
            <div className="text-sm text-gray-600">
              Ingest markdown files from a local folder (preserves structure)
            </div>
          </div>
        </label>
      </div>
    </div>
  );
}
