interface MarkdownConfigProps {
  readonly markdownFolderPath: string;
  readonly setMarkdownFolderPath: (path: string) => void;
}

export function MarkdownConfig({
  markdownFolderPath,
  setMarkdownFolderPath,
}: MarkdownConfigProps) {
  return (
    <>
      <div>
        <label
          htmlFor="markdown-folder"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          Markdown Folder Path *
        </label>
        <input
          id="markdown-folder"
          type="text"
          value={markdownFolderPath}
          onChange={(e) => {
            setMarkdownFolderPath(e.target.value);
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="C:\Documentation\markdown"
        />
        <p className="mt-1 text-xs text-gray-500">
          Path to folder containing .md files (will recursively process
          subfolders)
        </p>
      </div>

      <div className="p-3 bg-green-50 border border-green-200 rounded-md">
        <p className="text-sm text-green-800">
          ✅ Markdown structure and hierarchy will be preserved in metadata
        </p>
      </div>
    </>
  );
}
