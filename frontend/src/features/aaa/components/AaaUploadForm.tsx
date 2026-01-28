interface AaaUploadFormProps {
  readonly files: FileList | null;
  readonly setFiles: (files: FileList | null) => void;
  readonly handleUploadDocuments: (e: React.FormEvent) => Promise<void>;
  readonly handleAnalyzeDocuments: () => Promise<void>;
  readonly loading: boolean;
}

export function AaaUploadForm({
  files,
  setFiles,
  handleUploadDocuments,
  handleAnalyzeDocuments,
  loading,
}: AaaUploadFormProps) {
  return (
    <form
      onSubmit={(e) => {
        void handleUploadDocuments(e);
      }}
      className="space-y-3"
    >
      <div>
        <label
          htmlFor="file-input"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          Documents
        </label>
        <input
          id="file-input"
          type="file"
          multiple
          onChange={(e) => {
            setFiles(e.target.files);
          }}
          className="block w-full text-sm text-gray-700"
        />
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={files === null || files.length === 0 || loading}
          className="bg-blue-600 text-white px-3 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          Upload
        </button>
        <button
          type="button"
          onClick={() => void handleAnalyzeDocuments()}
          disabled={loading}
          className="bg-green-600 text-white px-3 py-2 rounded-md hover:bg-green-700 disabled:opacity-50 text-sm"
        >
          Analyze
        </button>
      </div>
    </form>
  );
}
