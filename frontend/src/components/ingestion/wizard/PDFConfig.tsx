import { ArrayInput } from "./ArrayInput";

interface PDFConfigProps {
  readonly pdfLocalPaths: string[];
  readonly setPdfLocalPaths: (paths: string[]) => void;
  readonly pdfUrls: string[];
  readonly setPdfUrls: (urls: string[]) => void;
  readonly pdfFolderPath: string;
  readonly setPdfFolderPath: (path: string) => void;
}

export function PDFConfig({
  pdfLocalPaths,
  setPdfLocalPaths,
  pdfUrls,
  setPdfUrls,
  pdfFolderPath,
  setPdfFolderPath,
}: PDFConfigProps) {
  return (
    <>
      <ArrayInput
        label="Local PDF Paths"
        values={pdfLocalPaths}
        onChange={setPdfLocalPaths}
        placeholder="C:\Documents\file.pdf"
        helpText="Absolute paths to PDF files on your computer"
      />

      <ArrayInput
        label="Online PDF URLs"
        values={pdfUrls}
        onChange={setPdfUrls}
        placeholder="https://example.com/document.pdf"
        helpText="Direct URLs to PDF files"
      />

      <div>
        <label
          htmlFor="pdf-folder"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          PDF Folder Path
        </label>
        <input
          id="pdf-folder"
          type="text"
          value={pdfFolderPath}
          onChange={(e) => {
            setPdfFolderPath(e.target.value);
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="C:\Documents\PDFs"
        />
        <p className="mt-1 text-xs text-gray-500">
          Process all PDF files in this folder
        </p>
      </div>

      <div className="p-3 bg-amber-50 border border-amber-200 rounded-md">
        <p className="text-sm text-amber-800">
          ⚠️ At least one PDF source (local path, URL, or folder) is
          required
        </p>
      </div>
    </>
  );
}
