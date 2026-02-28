import { Send } from "lucide-react";
import type { SyntheticEvent, ChangeEvent, KeyboardEvent } from "react";

interface ChatInputProps {
  readonly input: string;
  readonly sending: boolean;
  readonly isInputDisabled: boolean;
  readonly onSubmit: (event: SyntheticEvent<HTMLFormElement>) => void;
  readonly onInputChange: (event: ChangeEvent<HTMLInputElement>) => void;
  readonly onKeyDown: (event: KeyboardEvent<HTMLInputElement>) => void;
}

export function ChatInputForm({
  input,
  sending,
  isInputDisabled,
  onSubmit,
  onInputChange,
  onKeyDown,
}: ChatInputProps) {
  return (
    <div className="border-t border-border p-4 bg-card">
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={onInputChange}
          onKeyDown={onKeyDown}
          placeholder="Type your message... (Cmd+Enter to send)"
          disabled={sending}
          className="flex-1 px-4 py-3 border border-border-stronger rounded-lg focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent disabled:bg-surface disabled:text-dim"
        />
        <button
          type="submit"
          disabled={isInputDisabled}
          className="px-6 py-3 bg-brand text-inverse rounded-lg hover:bg-brand-strong disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          <Send className="h-4 w-4" />
          <span className="hidden sm:inline">Send</span>
        </button>
      </form>
      <p className="text-xs text-dim mt-2">
        Use{" "}
        <kbd className="px-1 py-0.5 bg-muted border border-border-stronger rounded text-xs">
          Cmd
        </kbd>{" "}
        +{" "}
        <kbd className="px-1 py-0.5 bg-muted border border-border-stronger rounded text-xs">
          Enter
        </kbd>{" "}
        to send
      </p>
    </div>
  );
}
