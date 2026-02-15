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
          className="block text-sm font-medium text-secondary mb-1"
        >
          URL Prefix Filter
        </label>
        <input
          id="url-prefix"
          type="text"
          value={urlPrefix}
          onChange={(e) => {
            setUrlPrefix(e.target.value);
          }}
          className="w-full px-3 py-2 border border-border-stronger rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
          placeholder="https://example.com/docs/section/"
        />
        <p className="mt-1 text-xs text-dim">
          Auto-filled from first URL. Only pages starting with this prefix will be crawled. Edit to restrict scope further.
        </p>
      </div>
    </>
  );
}

