import { KbQueryResponse } from "../../types/api";

interface Props {
  readonly response: KbQueryResponse | null;
  readonly onFollowUp: (question: string) => void;
}

export function KBQueryResults({ response, onFollowUp }: Props) {
  if (response === null) {
    return null;
  }

  const sources = Array.isArray(response.sources) ? response.sources : [];
  const followUps = Array.isArray(response.suggestedFollowUps)
    ? response.suggestedFollowUps
    : [];

  if (!response.hasResults) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
        <p className="text-yellow-800">
          No relevant information found. Try rephrasing your question or being
          more specific.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Answer */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Answer</h2>
        <div className="prose prose-blue max-w-none">
          <p className="text-gray-800 whitespace-pre-wrap">{response.answer}</p>
        </div>
      </div>

      {/* Sources */}
      {sources.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Sources ({sources.length})
          </h2>
          <div className="space-y-3">
            {sources.map((source) => (
              <div
                key={`${source.url}-${source.section}`}
                className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      {source.title}
                    </a>
                    <div className="flex items-center gap-3 mt-1">
                      {source.kbName !== undefined && source.kbName !== "" && (
                        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded font-medium">
                          {source.kbName}
                        </span>
                      )}
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                        {source.section}
                      </span>
                      <span className="text-xs text-gray-500">
                        Relevance: {(source.score * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Suggested Follow-ups */}
      {followUps.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-blue-900 mb-3">
              Suggested Follow-up Questions
            </h2>
            <div className="space-y-2">
              {followUps.map((followUp) => (
                <button
                  key={followUp}
                  onClick={() => { onFollowUp(followUp); }}
                  className="block w-full text-left px-4 py-2 bg-white border border-blue-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-colors"
                >
                  <span className="text-blue-700">💬 {followUp}</span>
                </button>
              ))}
            </div>
          </div>
        )}
    </div>
  );
}
