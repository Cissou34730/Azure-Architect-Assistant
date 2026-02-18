import { KbQueryResponse, KbSource } from "../../types/api";
import { Card, Button } from "../common";

interface SourceItemProps {
  readonly source: KbSource;
}

function SourceItem({ source }: SourceItemProps) {
  return (
    <div className="border border-border rounded-lg p-4 hover:border-brand-line transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand hover:text-brand-strong font-medium"
          >
            {source.title}
          </a>
          <div className="flex items-center gap-3 mt-1">
            {source.kbName !== undefined && source.kbName !== "" && (
              <span className="text-xs bg-brand-soft text-brand-strong px-2 py-1 rounded font-medium">
                {source.kbName}
              </span>
            )}
            <span className="text-xs bg-muted text-secondary px-2 py-1 rounded">
              {source.section}
            </span>
            <span className="text-xs text-dim">
              Relevance: {(source.score * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

interface Props {
  readonly response: KbQueryResponse | null;
  readonly onFollowUp: (question: string) => void;
}

export function KBQueryResults({ response, onFollowUp }: Props) {
  if (response === null) {
    return null;
  }

  const sources = response.sources;
  const followUps = response.suggestedFollowUps ?? [];

  if (!response.hasResults) {
    return (
      <div className="bg-warning-soft border border-warning-line rounded-lg p-6">
        <p className="text-warning-strong">
          No relevant information found. Try rephrasing your question or being
          more specific.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Answer */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold text-foreground mb-4">Answer</h2>
        <div className="prose prose max-w-none">
          <p className="text-foreground whitespace-pre-wrap">{response.answer}</p>
        </div>
      </Card>

      {/* Sources */}
      {sources.length > 0 && (
        <Card className="p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">
            Sources ({sources.length})
          </h2>
          <div className="space-y-3">
            {sources.map((source, index) => (
              <SourceItem
                key={`${source.url}-${index}`} // eslint-disable-line react/no-array-index-key
                source={source}
              />
            ))}
          </div>
        </Card>
      )}

      {/* Suggested Follow-ups */}
      {followUps.length > 0 && (
        <div className="bg-brand-soft border border-brand-line rounded-lg p-6">
          <h2 className="text-lg font-semibold text-brand-strong mb-3">
            Suggested Follow-up Questions
          </h2>
          <div className="space-y-2">
            {followUps.map((followUp) => (
              <Button
                key={followUp}
                type="button"
                variant="ghost"
                className="block w-full text-left"
                onClick={() => {
                  onFollowUp(followUp);
                }}
              >
                <span className="text-brand-strong">💬 {followUp}</span>
              </Button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}



