import { Project } from '../services/apiService';

interface DocumentsPanelProps {
  selectedProject: Project;
  textRequirements: string;
  onTextRequirementsChange: (text: string) => void;
  onSaveTextRequirements: () => void;
  files: FileList | null;
  onFilesChange: (files: FileList | null) => void;
  onUploadDocuments: (e: React.FormEvent) => void;
  onAnalyzeDocuments: () => void;
  loading: boolean;
  loadingMessage: string;
}

export function DocumentsPanel({
  selectedProject,
  textRequirements,
  onTextRequirementsChange,
  onSaveTextRequirements,
  files,
  onFilesChange,
  onUploadDocuments,
  onAnalyzeDocuments,
  loading,
  loadingMessage,
}: DocumentsPanelProps) {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Documents & Requirements</h2>
      
      <div className="mb-6">
        <h3 className="font-semibold mb-2">Text Requirements</h3>
        <textarea
          value={textRequirements}
          onChange={(e) => onTextRequirementsChange(e.target.value)}
          placeholder="Describe your project requirements here..."
          className="w-full px-3 py-2 border border-gray-300 rounded-md mb-2 text-sm"
          rows={5}
        />
        <button
          onClick={onSaveTextRequirements}
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 mb-4"
        >
          Save Requirements
        </button>
      </div>
      
      <h3 className="font-semibold mb-2">Upload Documents</h3>
      <form onSubmit={onUploadDocuments} className="mb-4">
        <input
          id="file-input"
          type="file"
          multiple
          title="Select files to upload"
          onChange={(e) => onFilesChange(e.target.files)}
          className="w-full mb-2"
        />
        <button
          type="submit"
          disabled={loading || !files}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 mr-2"
        >
          Upload Documents
        </button>
      </form>
      
      <button
        onClick={onAnalyzeDocuments}
        disabled={loading || (!textRequirements.trim() && !selectedProject.textRequirements?.trim())}
        className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
      >
        {loading && loadingMessage.includes('Analyzing') ? (
          <>
            <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Analyzing...</span>
          </>
        ) : 'Analyze Requirements'}
      </button>
      
      {loading && loadingMessage.includes('Analyzing') && (
        <p className="text-sm text-blue-600 mt-2">{loadingMessage}</p>
      )}
      
      {!textRequirements.trim() && !selectedProject.textRequirements?.trim() && (
        <p className="text-sm text-gray-500 mt-2">Please add text requirements or upload documents to enable analysis.</p>
      )}
    </div>
  );
}
