interface FileUploadProps {
  readonly onFilesChange: (files: FileList | null) => void;
  readonly onUpload: (e: React.FormEvent) => void;
  readonly loading: boolean;
  readonly files: FileList | null;
}

export function FileUpload({
  onFilesChange,
  onUpload,
  loading,
  files,
}: FileUploadProps) {
  return (
    <>
      <h3 className="font-semibold mb-2">Upload Documents</h3>
      <form onSubmit={onUpload} className="mb-4">
        <input
          id="file-input"
          type="file"
          multiple
          title="Select files to upload"
          onChange={(e) => {
            onFilesChange(e.target.files);
          }}
          className="w-full mb-2"
        />
        <button
          type="submit"
          disabled={loading || files === null}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 mr-2"
        >
          Upload Documents
        </button>
      </form>
    </>
  );
}
