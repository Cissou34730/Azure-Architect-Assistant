import { ChevronRight, MessageCircle } from "lucide-react";
import { CenterChatArea } from "./CenterChatArea";

interface RightChatPanelProps {
  readonly onToggle: () => void;
}

export function RightChatPanel({ onToggle }: RightChatPanelProps) {
  return (
    <div className="flex flex-col h-full bg-white">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white shrink-0">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-blue-50 flex items-center justify-center">
            <MessageCircle className="h-4 w-4 text-blue-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">Chatbot</p>
            <p className="text-xs text-gray-500">Assistant</p>
          </div>
        </div>
        <button
          onClick={onToggle}
          className="p-1 hover:bg-gray-100 rounded transition-colors"
          title="Hide chat panel"
          type="button"
        >
          <ChevronRight className="h-5 w-5 text-gray-600" />
        </button>
      </div>

      <div className="flex-1 overflow-hidden">
        <CenterChatArea />
      </div>
    </div>
  );
}
