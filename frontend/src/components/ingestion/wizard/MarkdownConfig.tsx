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
          className="block text-sm font-medium text-secondary mb-1"
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
          className="w-full px-3 py-2 border border-border-stronger rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
          placeholder="C:\Documentation\markdown"
        />
        <p className="mt-1 text-xs text-dim">
          Path to folder containing .md files (will recursively process
          subfolders)
        </p>
      </div>

      <div className="p-3 bg-success-soft border border-success-line rounded-md">
        <p className="text-sm text-success-strong">
          ✅ Markdown structure and hierarchy will be preserved in metadata
        </p>
      </div>
    </>
  );
}


