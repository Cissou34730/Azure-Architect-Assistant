import { Ambiguity } from "../../types/api";

interface AmbiguitySectionProps {
  readonly ambiguities: readonly Ambiguity[];
}

export function AmbiguitySection({ ambiguities }: AmbiguitySectionProps) {
  if (ambiguities.length === 0) {
    return null;
  }

  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mt-8">
      <h2 className="text-xl font-semibold text-yellow-900 mb-4">
        Detected Ambiguities ({ambiguities.length})
      </h2>
      <div className="space-y-3">
        {ambiguities.map((ambiguity) => (
          <div
            key={ambiguity.id}
            className={`bg-white border rounded-lg p-4 ${
              ambiguity.resolved ? "border-green-300" : "border-yellow-300"
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-medium px-2 py-1 rounded bg-yellow-100 text-yellow-800">
                    AMBIGUITY
                  </span>
                  {ambiguity.resolved && (
                    <span className="text-xs font-medium px-2 py-1 rounded bg-green-100 text-green-800">
                      RESOLVED
                    </span>
                  )}
                </div>
                {ambiguity.ambiguousText !== "" && (
                  <p className="text-gray-800 mb-2 font-medium">
                    {ambiguity.ambiguousText}
                  </p>
                )}
                {ambiguity.suggestedClarification !== undefined &&
                  ambiguity.suggestedClarification !== "" && (
                    <p className="text-sm text-gray-600 bg-blue-50 p-3 rounded border border-blue-200">
                      <strong>Suggested:</strong>{" "}
                      {ambiguity.suggestedClarification}
                    </p>
                  )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
