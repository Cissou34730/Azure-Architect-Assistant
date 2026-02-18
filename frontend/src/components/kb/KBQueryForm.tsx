import { Card, Button } from "../common";

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
      <Card className="p-6">
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
          className="w-full px-4 py-2 border border-border-stronger rounded-lg focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
          disabled={isLoading}
        />
        <div className="flex justify-between items-center mt-4">
          <Button
            type="submit"
            variant="primary"
            disabled={isLoading || question.trim() === ""}
            isLoading={isLoading}
          >
            {isLoading ? "Searching..." : "Search Knowledge Bases"}
          </Button>
          <button
            type="button"
            onClick={onRefresh}
            className="text-secondary hover:text-foreground"
          >
            🔄 Refresh Status
          </button>
        </div>
      </Card>
    </form>
  );
}



