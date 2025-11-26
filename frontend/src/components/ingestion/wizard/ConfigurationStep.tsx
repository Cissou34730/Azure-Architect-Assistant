/**
 * Source Configuration Step Component
 */

import { SourceType } from '../../../types/ingestion';
import { ArrayInput } from './ArrayInput';

interface ConfigurationStepProps {
  sourceType: SourceType;
  startUrls: string[];
  setStartUrls: (urls: string[]) => void;
  allowedDomains: string[];
  setAllowedDomains: (domains: string[]) => void;
  pathPrefix: string;
  setPathPrefix: (prefix: string) => void;
  followLinks: boolean;
  setFollowLinks: (follow: boolean) => void;
  maxPages: number;
  setMaxPages: (max: number) => void;
  urls: string[];
  setUrls: (urls: string[]) => void;
}

export function ConfigurationStep({
  sourceType,
  startUrls,
  setStartUrls,
  allowedDomains,
  setAllowedDomains,
  pathPrefix,
  setPathPrefix,
  followLinks,
  setFollowLinks,
  maxPages,
  setMaxPages,
  urls,
  setUrls,
}: ConfigurationStepProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Source Configuration</h3>

      {sourceType === 'web_documentation' ? (
        <>
          <ArrayInput
            label="Start URLs *"
            values={startUrls}
            onChange={setStartUrls}
            placeholder="https://docs.example.com"
            helpText="Entry points for the crawler to begin from"
          />

          <ArrayInput
            label="Allowed Domains"
            values={allowedDomains}
            onChange={setAllowedDomains}
            placeholder="docs.example.com"
            helpText="Restrict crawling to these domains (optional)"
          />

          <div>
            <label htmlFor="path-prefix" className="block text-sm font-medium text-gray-700 mb-1">
              Path Prefix
            </label>
            <input
              id="path-prefix"
              type="text"
              value={pathPrefix}
              onChange={(e) => setPathPrefix(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="/docs"
            />
            <p className="mt-1 text-xs text-gray-500">
              Only crawl URLs starting with this path (optional)
            </p>
          </div>

          <div className="flex items-center gap-2">
            <input
              id="follow-links-docs"
              type="checkbox"
              checked={followLinks}
              onChange={(e) => setFollowLinks(e.target.checked)}
              className="rounded border-gray-300"
            />
            <label htmlFor="follow-links-docs" className="text-sm text-gray-700">
              Follow links to discover more pages
            </label>
          </div>

          <div>
            <label htmlFor="max-pages" className="block text-sm font-medium text-gray-700 mb-1">
              Max Pages
            </label>
            <input
              id="max-pages"
              type="number"
              value={maxPages}
              onChange={(e) => setMaxPages(parseInt(e.target.value))}
              min={1}
              max={10000}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              Maximum number of pages to crawl
            </p>
          </div>
        </>
      ) : (
        <>
          <ArrayInput
            label="URLs *"
            values={urls}
            onChange={setUrls}
            placeholder="https://example.com/article"
            helpText="Specific web pages to include"
          />

          <div className="flex items-center gap-2">
            <input
              id="follow-links-generic"
              type="checkbox"
              checked={followLinks}
              onChange={(e) => setFollowLinks(e.target.checked)}
              className="rounded border-gray-300"
            />
            <label htmlFor="follow-links-generic" className="text-sm text-gray-700">
              Follow links to discover related pages
            </label>
          </div>
        </>
      )}
    </div>
  );
}
