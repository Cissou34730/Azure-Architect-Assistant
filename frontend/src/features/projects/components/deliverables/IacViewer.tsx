import { useState } from "react";
import { Code, Download, Copy, CheckCircle, AlertCircle } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Card, CardHeader, CardTitle, CardContent, Badge, EmptyState } from "../../../../components/common";
import type { IacArtifact, IacFile } from "../../../../types/api";

interface IacViewerProps {
  iacArtifacts: readonly IacArtifact[];
}

export function IacViewer({ iacArtifacts }: IacViewerProps) {
  const [selectedArtifact, setSelectedArtifact] = useState<IacArtifact | null>(
    iacArtifacts.length > 0 ? iacArtifacts[0] : null
  );
  const [selectedFileIndex, setSelectedFileIndex] = useState(0);
  const [copied, setCopied] = useState(false);

  if (iacArtifacts.length === 0) {
    return (
      <EmptyState
        icon={Code}
        title="No IaC artifacts yet"
        description="Generate Infrastructure as Code using the Workspace chat"
        action={
          <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm">
            Go to Workspace
          </button>
        }
      />
    );
  }

  const handleCopy = async (content: string) => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = (file: IacFile) => {
    if (!file.content) return;
    const blob = new Blob([file.content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = file.path || "code.txt";
    a.click();
    URL.revokeObjectURL(url);
  };

  const currentFile = selectedArtifact?.files?.[selectedFileIndex];

  return (
    <div className="space-y-6">
      {/* Artifact Selector */}
      {iacArtifacts.length > 1 && (
        <div className="flex gap-2 flex-wrap">
          {iacArtifacts.map((artifact, idx) => (
            <button
              key={artifact.id || idx}
              onClick={() => {
                setSelectedArtifact(artifact);
                setSelectedFileIndex(0);
              }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedArtifact === artifact
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {artifact.createdAt
                ? new Date(artifact.createdAt).toLocaleDateString()
                : `Artifact ${idx + 1}`}
            </button>
          ))}
        </div>
      )}

      {selectedArtifact && (
        <Card>
          {/* Header with Validation Status */}
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle>Infrastructure as Code</CardTitle>
                {selectedArtifact.createdAt && (
                  <p className="text-sm text-gray-600 mt-1">
                    Generated: {new Date(selectedArtifact.createdAt).toLocaleString()}
                  </p>
                )}
              </div>
              <button
                onClick={() => alert("Download all as ZIP - Coming soon")}
                data-download-all-iac
                className="flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-sm"
              >
                <Download className="h-4 w-4" />
                Download All
              </button>
            </div>

            {selectedArtifact.validationResults && selectedArtifact.validationResults.length > 0 && (
              <div className="mt-4 space-y-2">
                <h4 className="text-sm font-medium text-gray-700">Validation Results</h4>
                <div className="flex flex-wrap gap-2">
                  {selectedArtifact.validationResults.map((result, idx) => (
                    <div
                      key={idx}
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
                          result.status?.toLowerCase() === "passed" ? "success" : "warning"
                        }
                        size="sm"
                      >
                        {result.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardHeader>

          <CardContent className="p-0">
            {/* File Tabs */}
            {selectedArtifact.files && selectedArtifact.files.length > 0 && (
              <div className="border-b border-gray-200 flex overflow-x-auto">
                {selectedArtifact.files.map((file, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedFileIndex(idx)}
                    className={`px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                      selectedFileIndex === idx
                        ? "border-blue-600 text-blue-600 bg-blue-50"
                        : "border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                    }`}
                  >
                    {file.path || `File ${idx + 1}`}
                    {file.format && (
                      <Badge variant="default" size="sm" className="ml-2">
                        {file.format}
                      </Badge>
                    )}
                  </button>
                ))}
              </div>
            )}

            {/* Code Viewer */}
            {currentFile && currentFile.content ? (
              <div className="relative">
                <div className="absolute top-2 right-2 z-10 flex gap-2">
                  <button
                    onClick={() => handleCopy(currentFile.content!)}
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
                    onClick={() => handleDownload(currentFile)}
                    className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors text-sm"
                  >
                    <Download className="h-4 w-4" />
                    Download
                  </button>
                </div>
                <SyntaxHighlighter
                  language={getLanguageFromFormat(currentFile.format || "")}
                  style={oneDark}
                  customStyle={{
                    margin: 0,
                    borderRadius: 0,
                    maxHeight: "600px",
                  }}
                >
                  {currentFile.content}
                </SyntaxHighlighter>
              </div>
            ) : (
              <div className="p-12 text-center text-gray-500">
                No file content available
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function getLanguageFromFormat(format: string): string {
  const f = format.toLowerCase();
  if (f.includes("bicep")) return "bicep";
  if (f.includes("terraform") || f.includes("tf")) return "hcl";
  if (f.includes("json")) return "json";
  if (f.includes("yaml") || f.includes("yml")) return "yaml";
  return "text";
}
