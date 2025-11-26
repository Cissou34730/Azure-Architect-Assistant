/**
 * Review Configuration Step Component
 */

import { SourceType } from '../../../types/ingestion';

interface ReviewStepProps {
  name: string;
  kbId: string;
  description: string;
  sourceType: SourceType;
  startUrls: string[];
  allowedDomains: string[];
  pathPrefix: string;
  followLinks: boolean;
  maxPages: number;
  urls: string[];
}

export function ReviewStep({
  name,
  kbId,
  description,
  sourceType,
  startUrls,
  allowedDomains,
  pathPrefix,
  followLinks,
  maxPages,
  urls,
}: ReviewStepProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Review Configuration</h3>

      <div className="bg-gray-50 rounded-lg p-4 space-y-3">
        <div>
          <div className="text-sm font-medium text-gray-700">Name</div>
          <div className="text-sm text-gray-900">{name}</div>
        </div>

        <div>
          <div className="text-sm font-medium text-gray-700">KB ID</div>
          <div className="text-sm text-gray-900 font-mono">{kbId}</div>
        </div>

        {description && (
          <div>
            <div className="text-sm font-medium text-gray-700">Description</div>
            <div className="text-sm text-gray-900">{description}</div>
          </div>
        )}

        <div>
          <div className="text-sm font-medium text-gray-700">Source Type</div>
          <div className="text-sm text-gray-900">
            {sourceType === 'web_documentation' ? 'Web Documentation' : 'Generic Web'}
          </div>
        </div>

        {sourceType === 'web_documentation' ? (
          <>
            <div>
              <div className="text-sm font-medium text-gray-700">Start URLs</div>
              <ul className="text-sm text-gray-900 list-disc list-inside">
                {startUrls.filter(url => url.trim()).map((url, i) => (
                  <li key={i} className="truncate">{url}</li>
                ))}
              </ul>
            </div>

            {allowedDomains.some(d => d.trim()) && (
              <div>
                <div className="text-sm font-medium text-gray-700">Allowed Domains</div>
                <ul className="text-sm text-gray-900 list-disc list-inside">
                  {allowedDomains.filter(d => d.trim()).map((domain, i) => (
                    <li key={i}>{domain}</li>
                  ))}
                </ul>
              </div>
            )}

            {pathPrefix && (
              <div>
                <div className="text-sm font-medium text-gray-700">Path Prefix</div>
                <div className="text-sm text-gray-900 font-mono">{pathPrefix}</div>
              </div>
            )}

            <div>
              <div className="text-sm font-medium text-gray-700">Settings</div>
              <ul className="text-sm text-gray-900 list-disc list-inside">
                <li>Follow links: {followLinks ? 'Yes' : 'No'}</li>
                <li>Max pages: {maxPages}</li>
              </ul>
            </div>
          </>
        ) : (
          <>
            <div>
              <div className="text-sm font-medium text-gray-700">URLs</div>
              <ul className="text-sm text-gray-900 list-disc list-inside">
                {urls.filter(url => url.trim()).map((url, i) => (
                  <li key={i} className="truncate">{url}</li>
                ))}
              </ul>
            </div>

            <div>
              <div className="text-sm font-medium text-gray-700">Settings</div>
              <ul className="text-sm text-gray-900 list-disc list-inside">
                <li>Follow links: {followLinks ? 'Yes' : 'No'}</li>
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
