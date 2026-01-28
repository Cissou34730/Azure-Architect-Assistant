import type { IacArtifact, IacFile, IacValidationResult } from "../../../types/api";

interface IacListProps {
  readonly iac: readonly IacArtifact[];
  readonly onDownload: (fileName: string, content: string) => void;
}

function IacItemFile({ file, onDownload }: { readonly file: IacFile; readonly onDownload: (n: string, c: string) => void }) {
  return (
    <div className="text-xs p-2 bg-gray-50 rounded border border-gray-100 flex justify-between items-center">
      <span className="font-mono truncate mr-2">
        {file.path !== "" ? file.path : "unnamed"} ({file.format})
      </span>
      <button
        onClick={() => {
          onDownload(file.path !== "" ? file.path : "download.txt", file.content);
        }}
        className="text-blue-600 hover:text-blue-800 font-medium"
      >
        Download
      </button>
    </div>
  );
}

function IacItemValidation({ validation }: { readonly validation: IacValidationResult }) {
  return (
    <div className="text-xs flex items-center justify-between">
      <span className="text-gray-600">{validation.tool !== "" ? validation.tool : "unknown"}:</span>
      <span
        className={`font-semibold ${
          validation.status === "pass" ? "text-green-600" : validation.status === "fail" ? "text-red-600" : "text-gray-500"
        }`}
      >
        {validation.status.toUpperCase()}
      </span>
    </div>
  );
}

function IacItem({ artifact, onDownload }: { readonly artifact: IacArtifact; readonly onDownload: (n: string, c: string) => void }) {
  const files = artifact.files;
  const validations = artifact.validationResults;

  return (
    <div className="bg-white p-4 rounded-md border border-gray-200">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="font-semibold text-gray-900">Artifact: {artifact.id}</h4>
          {artifact.createdAt !== undefined && artifact.createdAt !== "" && (
            <p className="text-xs text-gray-500 mt-1">{artifact.createdAt}</p>
          )}
        </div>
      </div>

      {files.length > 0 && (
        <div className="mt-3 space-y-2">
          <p className="text-xs font-medium text-gray-700">Files</p>
          {files.map((file, idx) => (
            <IacItemFile key={`file-${String(idx)}`} file={file} onDownload={onDownload} />
          ))}
        </div>
      )}

      {validations.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium text-gray-700 mb-1">Validations</p>
          <div className="space-y-1">
            {validations.map((validation, idx) => (
              <IacItemValidation key={`val-${String(idx)}`} validation={validation} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function IacList({ iac, onDownload }: IacListProps) {
  if (iac.length === 0) {
    return <p className="text-gray-600">No IaC artifacts yet. Generate via Agent chat.</p>;
  }

  const sortedIac = [...iac].sort((a, b) => (a.createdAt ?? "").localeCompare(b.createdAt ?? ""));

  return (
    <div className="space-y-3">
      {sortedIac.map((artifact) => (
        <IacItem key={artifact.id} artifact={artifact} onDownload={onDownload} />
      ))}
    </div>
  );
}
