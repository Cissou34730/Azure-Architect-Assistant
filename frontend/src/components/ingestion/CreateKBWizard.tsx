/**
 * Create KB Wizard Component
 * Multi-step wizard for creating a new knowledge base
 */

import { useState } from 'react';
import { SourceType, CreateKBRequest, WebDocumentationConfig, WebGenericConfig } from '../../types/ingestion';
import { createKB, startIngestion } from '../../services/ingestionApi';

interface CreateKBWizardProps {
  onSuccess: (kbId: string) => void;
  onCancel: () => void;
}

type WizardStep = 'basic' | 'source' | 'config' | 'review';

export function CreateKBWizard({ onSuccess, onCancel }: CreateKBWizardProps) {
  const [step, setStep] = useState<WizardStep>('basic');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [kbId, setKbId] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [sourceType, setSourceType] = useState<SourceType>('web_documentation');
  const [startUrls, setStartUrls] = useState<string[]>(['']);
  const [allowedDomains, setAllowedDomains] = useState<string[]>(['']);
  const [pathPrefix, setPathPrefix] = useState('');
  const [followLinks, setFollowLinks] = useState(true);
  const [maxPages, setMaxPages] = useState(1000);
  const [urls, setUrls] = useState<string[]>(['']);

  const generateKbId = (name: string) => {
    return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  };

  const handleNameChange = (value: string) => {
    setName(value);
    if (!kbId || kbId === generateKbId(name)) {
      setKbId(generateKbId(value));
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);

    try {
      // Build source config based on type
      let sourceConfig: WebDocumentationConfig | WebGenericConfig;

      if (sourceType === 'web_documentation') {
        sourceConfig = {
          start_urls: startUrls.filter(url => url.trim()),
          allowed_domains: allowedDomains.filter(d => d.trim()),
          path_prefix: pathPrefix || undefined,
          follow_links: followLinks,
          max_pages: maxPages,
        };
      } else {
        sourceConfig = {
          urls: urls.filter(url => url.trim()),
          follow_links: followLinks,
          max_depth: 1,
          same_domain_only: true,
        };
      }

      // Create KB
      const request: CreateKBRequest = {
        kb_id: kbId,
        name,
        description: description || undefined,
        source_type: sourceType,
        source_config: sourceConfig,
        embedding_model: 'text-embedding-3-small',
        chunk_size: 800,
        chunk_overlap: 120,
        profiles: ['chat', 'kb-query'],
        priority: 2,
      };

      await createKB(request);

      // Start ingestion
      await startIngestion(kbId);

      onSuccess(kbId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create KB');
    } finally {
      setLoading(false);
    }
  };

  const canProceed = () => {
    switch (step) {
      case 'basic':
        return kbId && name;
      case 'source':
        return sourceType;
      case 'config':
        if (sourceType === 'web_documentation') {
          return startUrls.some(url => url.trim());
        }
        return urls.some(url => url.trim());
      case 'review':
        return true;
      default:
        return false;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg max-w-3xl mx-auto">
      {/* Header */}
      <div className="px-6 py-4 border-b">
        <h2 className="text-2xl font-bold text-gray-900">Create Knowledge Base</h2>
        <div className="mt-4 flex justify-between items-center">
          {(['basic', 'source', 'config', 'review'] as WizardStep[]).map((s, i) => (
            <div key={s} className="flex items-center flex-1">
              <div className={`flex items-center justify-center w-8 h-8 rounded-full border-2 ${
                step === s ? 'border-blue-600 bg-blue-600 text-white' :
                ['basic', 'source', 'config', 'review'].indexOf(step) > i ? 'border-green-600 bg-green-600 text-white' :
                'border-gray-300 text-gray-400'
              }`}>
                {i + 1}
              </div>
              {i < 3 && (
                <div className={`flex-1 h-0.5 mx-2 ${
                  ['basic', 'source', 'config', 'review'].indexOf(step) > i ? 'bg-green-600' : 'bg-gray-300'
                }`} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="px-6 py-6 min-h-[400px]">
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <div className="text-sm text-red-600">{error}</div>
          </div>
        )}

        {/* Step 1: Basic Info */}
        {step === 'basic' && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">Basic Information</h3>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => handleNameChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Azure Architecture"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                KB ID *
              </label>
              <input
                type="text"
                value={kbId}
                onChange={(e) => setKbId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., azure-arch"
              />
              <p className="mt-1 text-xs text-gray-500">
                Unique identifier (lowercase, hyphens only)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Brief description of this knowledge base"
              />
            </div>
          </div>
        )}

        {/* Step 2: Source Type */}
        {step === 'source' && (
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
        )}

        {/* Step 3: Source Configuration */}
        {step === 'config' && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">Source Configuration</h3>

            {sourceType === 'web_documentation' ? (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Start URLs *
                  </label>
                  {startUrls.map((url, i) => (
                    <div key={i} className="flex gap-2 mb-2">
                      <input
                        type="url"
                        value={url}
                        onChange={(e) => {
                          const newUrls = [...startUrls];
                          newUrls[i] = e.target.value;
                          setStartUrls(newUrls);
                        }}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="https://docs.example.com"
                      />
                      {i > 0 && (
                        <button
                          onClick={() => setStartUrls(startUrls.filter((_, idx) => idx !== i))}
                          className="px-3 py-2 text-red-600 hover:bg-red-50 rounded-md"
                        >
                          Remove
                        </button>
                      )}
                    </div>
                  ))}
                  <button
                    onClick={() => setStartUrls([...startUrls, ''])}
                    className="text-sm text-blue-600 hover:text-blue-700"
                  >
                    + Add URL
                  </button>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Allowed Domains
                  </label>
                  {allowedDomains.map((domain, i) => (
                    <div key={i} className="flex gap-2 mb-2">
                      <input
                        type="text"
                        value={domain}
                        onChange={(e) => {
                          const newDomains = [...allowedDomains];
                          newDomains[i] = e.target.value;
                          setAllowedDomains(newDomains);
                        }}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="docs.example.com"
                      />
                      {i > 0 && (
                        <button
                          onClick={() => setAllowedDomains(allowedDomains.filter((_, idx) => idx !== i))}
                          className="px-3 py-2 text-red-600 hover:bg-red-50 rounded-md"
                        >
                          Remove
                        </button>
                      )}
                    </div>
                  ))}
                  <button
                    onClick={() => setAllowedDomains([...allowedDomains, ''])}
                    className="text-sm text-blue-600 hover:text-blue-700"
                  >
                    + Add Domain
                  </button>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Path Prefix (optional)
                  </label>
                  <input
                    type="text"
                    value={pathPrefix}
                    onChange={(e) => setPathPrefix(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="/en-us/azure/"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Max Pages
                  </label>
                  <input
                    type="number"
                    value={maxPages}
                    onChange={(e) => setMaxPages(parseInt(e.target.value) || 1000)}
                    min={1}
                    max={10000}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </>
            ) : (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  URLs *
                </label>
                {urls.map((url, i) => (
                  <div key={i} className="flex gap-2 mb-2">
                    <input
                      type="url"
                      value={url}
                      onChange={(e) => {
                        const newUrls = [...urls];
                        newUrls[i] = e.target.value;
                        setUrls(newUrls);
                      }}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="https://example.com/page"
                    />
                    {i > 0 && (
                      <button
                        onClick={() => setUrls(urls.filter((_, idx) => idx !== i))}
                        className="px-3 py-2 text-red-600 hover:bg-red-50 rounded-md"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ))}
                <button
                  onClick={() => setUrls([...urls, ''])}
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  + Add URL
                </button>
              </div>
            )}

            <div className="flex items-center">
              <input
                type="checkbox"
                checked={followLinks}
                onChange={(e) => setFollowLinks(e.target.checked)}
                className="mr-2"
              />
              <label className="text-sm text-gray-700">
                Follow links on pages
              </label>
            </div>
          </div>
        )}

        {/* Step 4: Review */}
        {step === 'review' && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">Review & Create</h3>

            <div className="bg-gray-50 rounded-lg p-4 space-y-3">
              <div>
                <div className="text-xs text-gray-500">Name</div>
                <div className="font-medium">{name}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">KB ID</div>
                <div className="font-medium">{kbId}</div>
              </div>
              {description && (
                <div>
                  <div className="text-xs text-gray-500">Description</div>
                  <div className="font-medium">{description}</div>
                </div>
              )}
              <div>
                <div className="text-xs text-gray-500">Source Type</div>
                <div className="font-medium">
                  {sourceType === 'web_documentation' ? 'Web Documentation' : 'Generic Web'}
                </div>
              </div>
              {sourceType === 'web_documentation' ? (
                <>
                  <div>
                    <div className="text-xs text-gray-500">Start URLs</div>
                    <div className="font-medium text-sm">
                      {startUrls.filter(u => u.trim()).join(', ')}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500">Max Pages</div>
                    <div className="font-medium">{maxPages}</div>
                  </div>
                </>
              ) : (
                <div>
                  <div className="text-xs text-gray-500">URLs</div>
                  <div className="font-medium text-sm">
                    {urls.filter(u => u.trim()).join(', ')}
                  </div>
                </div>
              )}
            </div>

            <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
              <div className="text-sm text-blue-800">
                <strong>Next:</strong> Once created, the ingestion process will start automatically.
                You can monitor progress in real-time.
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-6 py-4 border-t flex justify-between">
        <button
          onClick={step === 'basic' ? onCancel : () => {
            const steps: WizardStep[] = ['basic', 'source', 'config', 'review'];
            const currentIndex = steps.indexOf(step);
            setStep(steps[currentIndex - 1]);
          }}
          disabled={loading}
          className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-md disabled:opacity-50"
        >
          {step === 'basic' ? 'Cancel' : 'Back'}
        </button>

        <button
          onClick={step === 'review' ? handleSubmit : () => {
            const steps: WizardStep[] = ['basic', 'source', 'config', 'review'];
            const currentIndex = steps.indexOf(step);
            setStep(steps[currentIndex + 1]);
          }}
          disabled={!canProceed() || loading}
          className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {loading ? 'Creating...' : step === 'review' ? 'Create & Start' : 'Next'}
        </button>
      </div>
    </div>
  );
}
