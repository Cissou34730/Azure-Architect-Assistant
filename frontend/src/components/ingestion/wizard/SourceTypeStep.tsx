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
      <h3 className="text-lg font-semibold text-foreground">Source Type</h3>

      <div className="space-y-3">
        <label
          className={`flex items-start p-4 border-2 rounded-lg cursor-pointer hover:bg-surface transition-colors ${
            sourceType === "website" ? "border-brand" : "border-border"
          }`}
        >
          <input
            type="radio"
            value="website"
            checked={sourceType === "website"}
            onChange={() => {
              setSourceType("website");
            }}
            className="mt-1"
          />
          <div className="ml-3">
            <div className="font-medium text-foreground">📄 Website</div>
            <div className="text-sm text-secondary">
              Crawl websites and documentation using Trafilatura (URLs or
              sitemap)
            </div>
          </div>
        </label>

        <label
          className={`flex items-start p-4 border-2 rounded-lg cursor-pointer hover:bg-surface transition-colors ${
            sourceType === "youtube" ? "border-brand" : "border-border"
          }`}
        >
          <input
            type="radio"
            value="youtube"
            checked={sourceType === "youtube"}
            onChange={() => {
              setSourceType("youtube");
            }}
            className="mt-1"
          />
          <div className="ml-3">
            <div className="font-medium text-foreground">🎥 YouTube</div>
            <div className="text-sm text-secondary">
              Extract and distill transcripts from YouTube videos with LLM
            </div>
          </div>
        </label>

        <label
          className={`flex items-start p-4 border-2 rounded-lg cursor-pointer hover:bg-surface transition-colors ${
            sourceType === "pdf" ? "border-brand" : "border-border"
          }`}
        >
          <input
            type="radio"
            value="pdf"
            checked={sourceType === "pdf"}
            onChange={() => {
              setSourceType("pdf");
            }}
            className="mt-1"
          />
          <div className="ml-3">
            <div className="font-medium text-foreground">📑 PDF Files</div>
            <div className="text-sm text-secondary">
              Upload local PDFs or provide URLs to online PDF documents
            </div>
          </div>
        </label>

        <label
          className={`flex items-start p-4 border-2 rounded-lg cursor-pointer hover:bg-surface transition-colors ${
            sourceType === "markdown" ? "border-brand" : "border-border"
          }`}
        >
          <input
            type="radio"
            value="markdown"
            checked={sourceType === "markdown"}
            onChange={() => {
              setSourceType("markdown");
            }}
            className="mt-1"
          />
          <div className="ml-3">
            <div className="font-medium text-foreground">📝 Markdown</div>
            <div className="text-sm text-secondary">
              Ingest markdown files from a local folder (preserves structure)
            </div>
          </div>
        </label>
      </div>
    </div>
  );
}

