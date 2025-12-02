/**
 * Review Configuration Step Component
 */

import { SourceType } from '../../../types/ingestion';

interface ReviewStepProps {
  name: string;
  kbId: string;
  description: string;
  sourceType: SourceType;
  // Website
  urls?: string[];
  sitemapUrl?: string;
  // YouTube
  videoUrls?: string[];
  // PDF
  pdfLocalPaths?: string[];
  pdfUrls?: string[];
  pdfFolderPath?: string;
  // Markdown
  markdownFolderPath?: string;
}

const sourceTypeLabels: Record<SourceType, string> = {
  website: '🌐 Website',
  web_documentation: '📚 Web Documentation',
  web_generic: '🌐 Generic Web',
  youtube: '🎥 YouTube',
  pdf: '📄 PDF Files',
  markdown: '📝 Markdown',
};

export function ReviewStep({
  name,
  kbId,
  description,
  sourceType,
  urls,
  sitemapUrl,
  videoUrls,
  pdfLocalPaths,
  pdfUrls,
  pdfFolderPath,
  markdownFolderPath,
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
          <div className="text-sm text-gray-900">{sourceTypeLabels[sourceType]}</div>
        </div>

        {sourceType === 'website' && (
          <>
            {sitemapUrl ? (
              <div>
                <div className="text-sm font-medium text-gray-700">Sitemap URL</div>
                <div className="text-sm text-gray-900 font-mono truncate">{sitemapUrl}</div>
              </div>
            ) : (
              <div>
                <div className="text-sm font-medium text-gray-700">URLs</div>
                <ul className="text-sm text-gray-900 list-disc list-inside">
                  {urls?.filter(url => url.trim()).map((url, i) => (
                    <li key={i} className="truncate">{url}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}

        {sourceType === 'youtube' && (
          <div>
            <div className="text-sm font-medium text-gray-700">Video URLs</div>
            <ul className="text-sm text-gray-900 list-disc list-inside">
              {videoUrls?.filter(url => url.trim()).map((url, i) => (
                <li key={i} className="truncate">{url}</li>
              ))}
            </ul>
          </div>
        )}

        {sourceType === 'pdf' && (
          <>
            {pdfLocalPaths && pdfLocalPaths.some(p => p.trim()) && (
              <div>
                <div className="text-sm font-medium text-gray-700">Local PDF Paths</div>
                <ul className="text-sm text-gray-900 list-disc list-inside">
                  {pdfLocalPaths.filter(p => p.trim()).map((path, i) => (
                    <li key={i} className="truncate font-mono">{path}</li>
                  ))}
                </ul>
              </div>
            )}

            {pdfUrls && pdfUrls.some(url => url.trim()) && (
              <div>
                <div className="text-sm font-medium text-gray-700">Online PDF URLs</div>
                <ul className="text-sm text-gray-900 list-disc list-inside">
                  {pdfUrls.filter(url => url.trim()).map((url, i) => (
                    <li key={i} className="truncate">{url}</li>
                  ))}
                </ul>
              </div>
            )}

            {pdfFolderPath && (
              <div>
                <div className="text-sm font-medium text-gray-700">PDF Folder</div>
                <div className="text-sm text-gray-900 font-mono">{pdfFolderPath}</div>
              </div>
            )}
          </>
        )}

        {sourceType === 'markdown' && (
          <div>
            <div className="text-sm font-medium text-gray-700">Markdown Folder</div>
            <div className="text-sm text-gray-900 font-mono">{markdownFolderPath}</div>
          </div>
        )}
      </div>

      <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
        <p className="text-sm text-blue-800">
          ✓ Click "Create KB" to start the ingestion process
        </p>
      </div>
    </div>
  );
}
