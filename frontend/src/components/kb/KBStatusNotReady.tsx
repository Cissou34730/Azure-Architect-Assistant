import { KbHealthResponse } from "../../types/api";

interface Props {
  readonly healthStatus: KbHealthResponse | null;
  readonly onRefresh: () => void;
}

export function KBStatusNotReady({ healthStatus, onRefresh }: Props) {
  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold text-yellow-800 mb-2">
          Knowledge Bases Not Ready
        </h2>
        <p className="text-yellow-700 mb-4">
          No knowledge bases are currently loaded. Status:{" "}
          {healthStatus?.overallStatus ?? "unknown"}
        </p>

        {healthStatus !== null && healthStatus.knowledgeBases.length > 0 && (
          <div className="mb-4 space-y-2">
              {healthStatus.knowledgeBases.map((kb) => (
                <div
                  key={kb.kbId}
                  className="flex items-center justify-between bg-white p-3 rounded"
                >
                  <div>
                    <span className="font-medium">{kb.kbName}</span>
                    <span className="text-sm text-gray-600 ml-2">
                      ({kb.kbId})
                    </span>
                  </div>
                  <div className="flex items-center">
                    <span
                      className={`px-2 py-1 rounded text-sm ${
                        kb.indexReady
                          ? "bg-green-100 text-green-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {kb.indexReady ? "✓ Ready" : "✗ Not Ready"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

        <button
          onClick={onRefresh}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
        >
          🔄 Refresh Status
        </button>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-800 mb-2">
          About Knowledge Base Query System
        </h3>
        <p className="text-blue-700 mb-2">
          This feature allows you to query multiple Azure knowledge bases
          including:
        </p>
        <ul className="list-disc list-inside text-blue-700 space-y-1">
          <li>Azure Well-Architected Framework</li>
          <li>Cloud Adoption Framework</li>
          <li>Architecture Center patterns and guidance</li>
          <li>Azure service documentation</li>
        </ul>
        <p className="text-blue-600 text-sm mt-4">
          <strong>Note:</strong> Knowledge bases are preloaded at startup. If
          none are ready, check the server logs or restart the Python service.
        </p>
      </div>
    </div>
  );
}
