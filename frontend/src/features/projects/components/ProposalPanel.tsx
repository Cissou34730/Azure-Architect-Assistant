interface ProposalPanelProps {
  architectureProposal: string;
  proposalStage: string;
  onGenerateProposal: () => void;
  loading: boolean;
}

export function ProposalPanel({
  architectureProposal,
  proposalStage,
  onGenerateProposal,
  loading,
}: ProposalPanelProps) {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">
        Azure Architecture Proposal
      </h2>

      <button
        onClick={onGenerateProposal}
        disabled={loading && proposalStage !== ""}
        className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 disabled:opacity-50 mb-4 flex items-center gap-2"
      >
        {loading && proposalStage ? "Generating..." : "Generate Proposal"}
      </button>

      {proposalStage && (
        <div className="mb-6 p-4 bg-linear-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg">
          <div className="flex items-start gap-3">
            <div className="shrink-0 mt-1">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce [animation-delay:150ms]" />
                <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-purple-900 mb-1">
                Thinking...
              </div>
              <div className="text-sm text-purple-700">{proposalStage}</div>
              <div className="mt-2 text-xs text-purple-600">
                This may take up to 40 seconds
              </div>
            </div>
          </div>
        </div>
      )}

      {architectureProposal && !proposalStage && (
        <div className="prose max-w-none">
          <pre className="whitespace-pre-wrap bg-gray-50 p-4 rounded-md border border-gray-200">
            {architectureProposal}
          </pre>
        </div>
      )}
    </div>
  );
}
