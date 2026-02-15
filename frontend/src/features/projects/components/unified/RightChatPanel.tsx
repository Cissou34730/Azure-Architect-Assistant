import { ChevronRight, MessageCircle } from "lucide-react";
import { CenterChatArea } from "./CenterChatArea";

interface RightChatPanelProps {
  readonly onToggle: () => void;
}

export function RightChatPanel({ onToggle }: RightChatPanelProps) {
  return (
    <div className="flex flex-col h-full bg-card">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-card shrink-0">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-brand-soft flex items-center justify-center">
            <MessageCircle className="h-4 w-4 text-brand" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">Chatbot</p>
            <p className="text-xs text-dim">Assistant</p>
          </div>
        </div>
        <button
          onClick={onToggle}
          className="p-1 hover:bg-muted rounded transition-colors"
          title="Hide chat panel"
          type="button"
        >
          <ChevronRight className="h-5 w-5 text-secondary" />
        </button>
      </div>

      <div className="flex-1 overflow-hidden">
        <CenterChatArea />
      </div>
    </div>
  );
}

