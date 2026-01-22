/**
 * Review Configuration Step Component
 */

import { SourceType } from "../../../types/ingestion";

const sourceTypeLabels: Record<SourceType, string> = {
  website: "🌐 Website",
  ["web_documentation"]: "📚 Web Documentation",
  ["web_generic"]: "🌐 Generic Web",
  youtube: "🎥 YouTube",
  pdf: "📄 PDF Files",
  markdown: "📝 Markdown",
};

interface ReviewStepProps {
  readonly name: string;
  readonly kbId: string;
  readonly description: string;
  readonly sourceType: SourceType;
  // Website
  readonly urls?: string[];
  // YouTube
  readonly videoUrls?: string[];
  // PDF
  readonly pdfLocalPaths?: string[];
  readonly pdfUrls?: string[];
  readonly pdfFolderPath?: string;
  // Markdown
  readonly markdownFolderPath?: string;
}

function List({ items }: { readonly items: string[] | undefined }) {
  if (items === undefined) return null;
  const filtered = items.filter((item) => item.trim() !== "");
  if (filtered.length === 0) return null;

  return (
    <ul className="text-sm list-disc list-inside">
      {filtered.map((item) => (
        <li key={item} className="truncate">
          {item}
        </li>
      ))}
    </ul>
  );
}

function WebsiteReview({ urls }: { readonly urls?: string[] }) {
  return (
    <div>
      <div className="text-sm font-medium text-gray-700">URLs</div>
      <List items={urls} />
    </div>
  );
}

interface YouTubeReviewProps {
  readonly videoUrls?: string[];
}

function YouTubeReview({ videoUrls }: YouTubeReviewProps) {
  return (
    <div>
      <div className="text-sm font-medium text-gray-700">Video URLs</div>
      <List items={videoUrls} />
    </div>
  );
}

interface PDFReviewProps {
  readonly pdfLocalPaths?: string[];
  readonly pdfUrls?: string[];
  readonly pdfFolderPath?: string;
}

function PDFReview({
  pdfLocalPaths,
  pdfUrls,
  pdfFolderPath,
}: PDFReviewProps) {
  return (
    <div className="space-y-3">
      <div>
        <div className="text-sm font-medium text-gray-700">Local PDF Paths</div>
        <List items={pdfLocalPaths} />
      </div>
      <div>
        <div className="text-sm font-medium text-gray-700">Online PDF URLs</div>
        <List items={pdfUrls} />
      </div>
      {pdfFolderPath !== undefined && pdfFolderPath !== "" && (
        <div>
          <div className="text-sm font-medium text-gray-700">PDF Folder</div>
          <div className="text-sm text-gray-900 font-mono">{pdfFolderPath}</div>
        </div>
      )}
    </div>
  );
}

interface MarkdownReviewProps {
  readonly markdownFolderPath?: string;
}

function MarkdownReview({ markdownFolderPath }: MarkdownReviewProps) {
  return (
    <div>
      <div className="text-sm font-medium text-gray-700">Markdown Folder</div>
      <div className="text-sm text-gray-900 font-mono">{markdownFolderPath}</div>
    </div>
  );
}

function SourceConfig({ config }: { readonly config: ReviewStepProps }) {
  const { sourceType } = config;

  switch (sourceType) {
    case "website":
    case "web_documentation":
    case "web_generic":
      return <WebsiteReview urls={config.urls} />;
    case "youtube":
      return <YouTubeReview videoUrls={config.videoUrls} />;
    case "pdf":
      return (
        <PDFReview
          pdfLocalPaths={config.pdfLocalPaths}
          pdfUrls={config.pdfUrls}
          pdfFolderPath={config.pdfFolderPath}
        />
      );
    case "markdown":
      return <MarkdownReview markdownFolderPath={config.markdownFolderPath} />;
    default:
      return null;
  }
}

export function ReviewStep(props: ReviewStepProps) {
  const { name, kbId, description, sourceType } = props;

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Review Configuration</h3>

      <div className="bg-gray-50 rounded-lg p-4 space-y-3">
        <div>
          <div className="text-sm font-medium text-gray-700">Name</div>
          <div className="text-sm text-gray-900">{name}</div>
        </div>

        <div>
          <div className="text-sm font-medium text-gray-700">KB ID</div>
          <div className="text-sm text-gray-900 font-mono">{kbId}</div>
        </div>

        {description !== "" && (
          <div>
            <div className="text-sm font-medium text-gray-700">Description</div>
            <div className="text-sm text-gray-900">{description}</div>
          </div>
        )}

        <div>
          <div className="text-sm font-medium text-gray-700">Source Type</div>
          <div className="text-sm text-gray-900">{sourceTypeLabels[sourceType]}</div>
        </div>

        <div className="pt-2 border-t border-gray-200">
          <SourceConfig config={props} />
        </div>
      </div>

      <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
        <p className="text-sm text-blue-800">✓ Click &quot;Create KB&quot; to start the ingestion process</p>
      </div>
    </div>
  );
}
