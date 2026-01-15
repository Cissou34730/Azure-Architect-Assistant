import { ArrayInput } from "./ArrayInput";

interface WebsiteConfigProps {
  readonly urls: string[];
  readonly setUrls: (urls: string[]) => void;
  readonly sitemapUrl: string;
  readonly setSitemapUrl: (url: string) => void;
  readonly urlPrefix: string;
  readonly setUrlPrefix: (prefix: string) => void;
}

export function WebsiteConfig({
  urls,
  setUrls,
  sitemapUrl,
  setSitemapUrl,
  urlPrefix,
  setUrlPrefix,
}: WebsiteConfigProps) {
  return (
    <>
      <div>
        <label
          htmlFor="sitemap-url"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          Sitemap URL (Optional)
        </label>
        <input
          id="sitemap-url"
          type="text"
          value={sitemapUrl}
          onChange={(e) => {
            setSitemapUrl(e.target.value);
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="https://example.com/sitemap.xml"
        />
        <p className="mt-1 text-xs text-gray-500">
          Provide sitemap URL to automatically crawl all pages, or specify
          individual URLs below
        </p>
      </div>

      {sitemapUrl !== "" && (
        <div>
          <label
            htmlFor="url-prefix"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            URL Prefix Filter (Recommended)
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
            Only ingest URLs starting with this prefix. Prevents crawling
            the entire site.
          </p>
        </div>
      )}

      {sitemapUrl === "" && (
        <ArrayInput
          label="URLs *"
          values={urls}
          onChange={setUrls}
          placeholder="https://example.com/page"
          helpText="Specific web pages to crawl (required if no sitemap provided)"
        />
      )}
    </>
  );
}
