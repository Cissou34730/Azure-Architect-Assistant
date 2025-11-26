/**
 * Source Type Selection Step Component
 */

import { SourceType } from '../../../types/ingestion';

interface SourceTypeStepProps {
  sourceType: SourceType;
  setSourceType: (type: SourceType) => void;
}

export function SourceTypeStep({ sourceType, setSourceType }: SourceTypeStepProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Source Type</h3>

      <div className="space-y-3">
        <label className={`flex items-start p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors ${
          sourceType === 'web_documentation' ? 'border-blue-600' : 'border-gray-200'
        }`}>
          <input
            type="radio"
            value="web_documentation"
            checked={sourceType === 'web_documentation'}
            onChange={(e) => setSourceType(e.target.value as SourceType)}
            className="mt-1"
          />
          <div className="ml-3">
            <div className="font-medium text-gray-900">Web Documentation</div>
            <div className="text-sm text-gray-600">
              Structured documentation sites (Microsoft Learn, Read the Docs, etc.)
            </div>
          </div>
        </label>

        <label className={`flex items-start p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors ${
          sourceType === 'web_generic' ? 'border-blue-600' : 'border-gray-200'
        }`}>
          <input
            type="radio"
            value="web_generic"
            checked={sourceType === 'web_generic'}
            onChange={(e) => setSourceType(e.target.value as SourceType)}
            className="mt-1"
          />
          <div className="ml-3">
            <div className="font-medium text-gray-900">Generic Web</div>
            <div className="text-sm text-gray-600">
              Any website with unstructured content
            </div>
          </div>
        </label>

        <label className="flex items-start p-4 border-2 border-gray-300 rounded-lg cursor-not-allowed bg-gray-50 opacity-50">
          <input
            type="radio"
            disabled
            className="mt-1"
          />
          <div className="ml-3">
            <div className="font-medium text-gray-900">Local Files</div>
            <div className="text-sm text-gray-600">
              Upload PDFs, DOCX, and other documents (Coming soon)
            </div>
          </div>
        </label>
      </div>
    </div>
  );
}
