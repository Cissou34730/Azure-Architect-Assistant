interface Props {
  readonly question: string;
  readonly isLoading: boolean;
  readonly onQuestionChange: (value: string) => void;
  readonly onSubmit: (e: React.FormEvent) => void;
  readonly onRefresh: () => void;
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
      <div className="bg-card rounded-lg shadow-md p-6">
        <label className="block text-sm font-medium text-secondary mb-2">
          Your Question
        </label>
        <textarea
          value={question}
          onChange={(e) => {
            onQuestionChange(e.target.value);
          }}
          placeholder="E.g., What are the best practices for securing Azure SQL databases?"
          rows={3}
          className="w-full px-4 py-2 border border-border-stronger rounded-lg focus:ring-2 focus:ring-brand focus:border-transparent"
          disabled={isLoading}
        />
        <div className="flex justify-between items-center mt-4">
          <button
            type="submit"
            disabled={isLoading || question.trim() === ""}
            className="bg-brand text-inverse px-6 py-2 rounded-lg hover:bg-brand-strong disabled:bg-border-stronger disabled:cursor-not-allowed flex items-center"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-inverse mr-2" />
                Searching...
              </>
            ) : (
              "Search Knowledge Bases"
            )}
          </button>
          <button
            type="button"
            onClick={onRefresh}
            className="text-secondary hover:text-foreground"
          >
            🔄 Refresh Status
          </button>
        </div>
      </div>
    </form>
  );
}



