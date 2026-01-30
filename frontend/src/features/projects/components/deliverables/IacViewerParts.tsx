import { useState, lazy } from "react";
import { Code, Download, Copy, CheckCircle, AlertCircle } from "lucide-react";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Card, CardHeader, CardTitle, CardContent, Badge } from "../../../../components/common";
import type { IacArtifact, IacFile } from "../../../../types/api";

// Lazy load SyntaxHighlighter to reduce initial bundle size
// eslint-disable-next-line @typescript-eslint/naming-convention -- React lazy component must be PascalCase
const SyntaxHighlighter = lazy(() =>
  import("react-syntax-highlighter").then((m) => ({ default: m.Prism })),
);

const SYNTAX_HIGHLIGHT_THRESHOLD = 800;

function getLanguageFromFormat(format: string): string {
  const f = format.toLowerCase();
  if (f.includes("bicep")) return "bicep";
  if (f.includes("terraform") || f.includes("tf")) return "hcl";
  if (f.includes("json")) return "json";
  if (f.includes("yaml") || f.includes("yml")) return "yaml";
  return "text";
}

interface ArtifactSelectorProps {
  readonly artifacts: readonly IacArtifact[];
  readonly selectedId: string | undefined;
  readonly onSelect: (artifact: IacArtifact) => void;
}

export function ArtifactSelector({
  artifacts,
  selectedId,
  onSelect,
}: ArtifactSelectorProps) {
  if (artifacts.length <= 1) return null;

  return (
    <div className="flex gap-2 flex-wrap">
      {artifacts.map((artifact, idx) => (
        <button
          key={artifact.id}
          type="button"
          onClick={() => {
            onSelect(artifact);
          }}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            selectedId === artifact.id
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          {artifact.createdAt !== undefined
            ? new Date(artifact.createdAt).toLocaleDateString()
            : `Artifact ${idx + 1}`}
        </button>
      ))}
    </div>
  );
}

interface ValidationResultsProps {
  readonly results: readonly {
    readonly tool?: string;
    readonly status?: string;
    readonly message?: string;
  }[];
}

function ValidationResults({ results }: ValidationResultsProps) {
  if (results.length === 0) return null;

  return (
    <div className="mt-4 space-y-2">
      <h4 className="text-sm font-medium text-gray-700">Validation Results</h4>
      <div className="flex flex-wrap gap-2">
        {results.map((result, idx) => (
          <div
            key={result.tool ?? idx}
            className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg"
          >
            {result.status?.toLowerCase() === "passed" ? (
              <CheckCircle className="h-4 w-4 text-green-600" />
            ) : (
              <AlertCircle className="h-4 w-4 text-amber-600" />
            )}
            <span className="text-sm font-medium text-gray-900">
              {result.tool}
            </span>
            <Badge
              variant={
                result.status?.toLowerCase() === "passed"
                  ? "success"
                  : "warning"
              }
              size="sm"
            >
              {result.status}
            </Badge>
          </div>
        ))}
      </div>
    </div>
  );
}

interface FileTabsProps {
  readonly files: readonly IacFile[];
  readonly selectedIndex: number;
  readonly onSelect: (index: number) => void;
}

function FileTabs({ files, selectedIndex, onSelect }: FileTabsProps) {
  if (files.length === 0) return null;

  return (
    <div className="border-b border-gray-200 flex overflow-x-auto">
      {files.map((file, idx) => (
        <button
          key={file.path}
          type="button"
          onClick={() => {
            onSelect(idx);
          }}
          className={`px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
            selectedIndex === idx
              ? "border-blue-600 text-blue-600 bg-blue-50"
              : "border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50"
          }`}
        >
          {file.path}
          <Badge variant="default" size="sm" className="ml-2">
            {file.format}
          </Badge>
        </button>
      ))}
    </div>
  );
}

interface CodeViewerProps {
  readonly file: IacFile;
}

// eslint-disable-next-line max-lines-per-function -- Keeping the viewer cohesive avoids splitting the UX flow.
function CodeViewer({ file }: CodeViewerProps) {
  const [copied, setCopied] = useState(false);
  const lineCount = file.content.split("\n").length;
  const shouldDeferHighlight = lineCount > SYNTAX_HIGHLIGHT_THRESHOLD;
  const [showHighlighted, setShowHighlighted] = useState(!shouldDeferHighlight);

  const handleCopy = () => {
    if (file.content === "") return;
    void navigator.clipboard.writeText(file.content).then(() => {
      setCopied(true);
      setTimeout(() => {
        setCopied(false);
      }, 2000);
    });
  };

  const handleDownload = () => {
    if (file.content === "") return;
    const blob = new Blob([file.content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = file.path;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (file.content === "") {
    return (
      <div className="p-12 text-center text-gray-500">
        No file content available
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="absolute top-2 right-2 z-10 flex gap-2">
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors text-sm"
        >
          {copied ? (
            <>
              <CheckCircle className="h-4 w-4" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="h-4 w-4" />
              Copy
            </>
          )}
        </button>
        <button
          type="button"
          onClick={handleDownload}
          className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors text-sm"
        >
          <Download className="h-4 w-4" />
          Download
        </button>
      </div>

      {shouldDeferHighlight && !showHighlighted ? (
        <div className="bg-gray-900 rounded-lg p-6 text-center">
          <Code className="h-12 w-12 text-gray-500 mx-auto mb-4" />
          <h4 className="text-white font-medium mb-2">Large file detected</h4>
          <p className="text-gray-400 text-sm mb-6">
            This file has {lineCount} lines. Syntax highlighting may impact performance.
          </p>
          <div className="flex justify-center gap-3">
            <button
              type="button"
              onClick={() => {
                setShowHighlighted(true);
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
            >
              Enable Highlighting
            </button>
            <button
              type="button"
              onClick={handleDownload}
              className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors text-sm"
            >
              Download File
            </button>
          </div>
          <pre className="mt-8 text-left text-xs text-gray-500 max-h-40 overflow-hidden opacity-50 select-none">
            {file.content.slice(0, 500)}...
          </pre>
        </div>
      ) : (
        <SyntaxHighlighter
          language={getLanguageFromFormat(file.format)}
          style={oneDark}
          customStyle={{
            margin: 0,
            borderRadius: "0.5rem",
            maxHeight: "600px",
          }}
        >
          {file.content}
        </SyntaxHighlighter>
      )}
    </div>
  );
}

interface ArtifactBoardProps {
  readonly selectedArtifact: IacArtifact;
  readonly selectedFileIndex: number;
  readonly onFileSelect: (index: number) => void;
}

export function ArtifactBoard({
  selectedArtifact,
  selectedFileIndex,
  onFileSelect,
}: ArtifactBoardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle>Infrastructure as Code</CardTitle>
            {selectedArtifact.createdAt !== undefined && (
              <p className="text-sm text-gray-600 mt-1">
                Generated: {new Date(selectedArtifact.createdAt).toLocaleString()}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={() => {
              alert("Download all as ZIP - Coming soon");
            }}
            data-download-all-iac
            className="flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-sm"
          >
            <Download className="h-4 w-4" />
            Download All
          </button>
        </div>

        {selectedArtifact.validationResults.length > 0 && (
          <ValidationResults results={selectedArtifact.validationResults} />
        )}
      </CardHeader>

      <CardContent className="p-0">
        <FileTabs
          files={selectedArtifact.files}
          selectedIndex={selectedFileIndex}
          onSelect={onFileSelect}
        />

        {selectedArtifact.files.length > 0 ? (
          <CodeViewer file={selectedArtifact.files[selectedFileIndex]} />
        ) : (
          <div className="p-12 text-center text-gray-500">No file selected</div>
        )}
      </CardContent>
    </Card>
  );
}
