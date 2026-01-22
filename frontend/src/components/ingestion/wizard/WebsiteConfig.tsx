import { ArrayInput } from "./ArrayInput";

interface WebsiteConfigProps {
  readonly urls: string[];
  readonly setUrls: (urls: string[]) => void;
  readonly urlPrefix: string;
  readonly setUrlPrefix: (prefix: string) => void;
}

export function WebsiteConfig({
  urls,
  setUrls,
  urlPrefix,
  setUrlPrefix,
}: WebsiteConfigProps) {
  return (
    <>
      <ArrayInput
        label="URLs *"
        values={urls}
        onChange={setUrls}
        placeholder="https://example.com/page"
        helpText="One or more URLs to ingest. If a single URL is provided, ingestion will crawl from that start URL."
      />

      <div>
        <label
          htmlFor="url-prefix"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          URL Prefix Filter (Optional)
        </label>
        <input
          id="url-prefix"
          type="text"
          value={urlPrefix}
          onChange={(e) => {
            setUrlPrefix(e.target.value);
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="https://example.com/docs/section/"
        />
        <p className="mt-1 text-xs text-gray-500">
          Only ingest URLs starting with this prefix. Prevents crawling the entire site.
        </p>
      </div>
    </>
  );
}
