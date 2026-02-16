import { FileText } from "lucide-react";
import type { ReferenceDocument } from "../../../../../types/api";

interface InputDocumentViewProps {
  readonly document: ReferenceDocument;
}

export function InputDocumentView({ document }: InputDocumentViewProps) {
  const normalizedUrl =
    typeof document.url === "string" ? document.url.trim() : "";
  const rawUrlIsValid =
    normalizedUrl !== "" &&
    normalizedUrl.toLowerCase() !== "null" &&
    normalizedUrl.toLowerCase() !== "undefined";
  const resolvedUrl = rawUrlIsValid ? resolveDocumentUrl(normalizedUrl) : undefined;
  const hasUrl = resolvedUrl !== undefined;
  const isPdf =
    (document.mimeType ?? "").toLowerCase().includes("pdf") ||
    document.title.toLowerCase().endsWith(".pdf");
  const previewUrl = hasUrl && resolvedUrl !== undefined
    ? isPdf
      ? withPdfViewerHash(resolvedUrl)
      : resolvedUrl
    : undefined;
  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-lg bg-info-soft flex items-center justify-center">
          <FileText className="h-5 w-5 text-info" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-foreground">{document.title}</h3>
          <p className="text-xs text-dim capitalize">{document.category}</p>
        </div>
      </div>
      <div className="rounded-lg border border-border bg-surface p-4 text-sm text-secondary">
        {hasUrl
          ? isPdf
            ? "PDF preview is rendered directly in the workspace pane."
            : "Document source is available and displayed in this pane when embedding is allowed by the source."
          : "Document preview is unavailable for this record."}
      </div>
      <div className="text-xs text-secondary">
        Parse status: {document.parseStatus ?? "unknown"} | Analysis status:{" "}
        {document.analysisStatus ?? "unknown"}
      </div>
      {document.parseError !== undefined &&
        document.parseError !== null &&
        document.parseError !== "" && (
          <div className="text-xs text-danger-strong">{document.parseError}</div>
        )}
      {hasUrl && isPdf && (
        <div className="rounded-lg border border-border bg-card overflow-hidden">
          <iframe
            title={`pdf-preview-${document.id}`}
            src={previewUrl}
            className="w-full h-[70vh]"
          />
        </div>
      )}
      {hasUrl && !isPdf && (
        <div className="rounded-lg border border-border bg-card overflow-hidden">
          <iframe
            title={`preview-${document.id}`}
            src={previewUrl}
            className="w-full h-[60vh]"
          />
        </div>
      )}
    </div>
  );
}

function resolveDocumentUrl(url: string): string {
  if (/^https?:\/\//i.test(url)) {
    return url;
  }

  if (url.startsWith("/")) {
    return url;
  }
  return `/${url}`;
}

function withPdfViewerHash(url: string): string {
  if (url.includes("#")) {
    return url;
  }
  return `${url}#view=FitH`;
}


