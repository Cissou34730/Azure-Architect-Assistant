interface Props {
  question: string;
  isLoading: boolean;
  onQuestionChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onRefresh: () => void;
}

export function KBQueryForm({
  question,
  isLoading,
  onQuestionChange,
  onSubmit,
  onRefresh,
}: Props) {
  return (
    <form onSubmit={onSubmit} className="mb-8">
      <div className="bg-white rounded-lg shadow-md p-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Your Question
        </label>
        <textarea
          value={question}
          onChange={(e) => onQuestionChange(e.target.value)}
          placeholder="E.g., What are the best practices for securing Azure SQL databases?"
          rows={3}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          disabled={isLoading}
        />
        <div className="flex justify-between items-center mt-4">
          <button
            type="submit"
            disabled={isLoading || !question.trim()}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Searching...
              </>
            ) : (
              "Search Knowledge Bases"
            )}
          </button>
          <button
            type="button"
            onClick={onRefresh}
            className="text-gray-600 hover:text-gray-800"
          >
            🔄 Refresh Status
          </button>
        </div>
      </div>
    </form>
  );
}
