import { Loader2, AlertCircle, RotateCcw } from "lucide-react";
import type { FailedMessage } from "../../hooks/useChatMessaging";

interface ChatFooterProps {
  readonly loading: boolean;
  readonly sending: boolean;
  readonly failedMessages: readonly FailedMessage[];
  readonly onRetryMessage?: (id: string) => Promise<void>;
}

export function ChatListFooter({
  loading,
  sending,
  failedMessages,
  onRetryMessage,
}: ChatFooterProps) {
  if (!loading && !sending && failedMessages.length === 0) return null;

  return (
    <div className="px-6 py-4 space-y-4">
      {(loading || sending) && (
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-brand-soft flex items-center justify-center shrink-0">
            <Loader2 className="h-5 w-5 text-brand animate-spin" />
          </div>
          <div className="bg-surface rounded-lg px-4 py-3 text-sm text-secondary">
            Thinking...
          </div>
        </div>
      )}

      {failedMessages.map((failed) => (
        <div
          key={failed.id}
          className="flex items-start gap-3 p-4 bg-danger-soft border border-danger-line rounded-lg text-danger-strong"
        >
          <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium">Message failed to send</p>
            <p className="text-sm opacity-90 line-clamp-1">{failed.content}</p>
            <p className="text-xs mt-1 text-danger">{failed.error}</p>
            <button
              type="button"
              onClick={() => {
                void onRetryMessage?.(failed.id);
              }}
              className="mt-2 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-danger-strong hover:text-danger-strong transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Retry Send
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
