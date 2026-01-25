import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { ChatPanel } from "../workspace/ChatPanel";
import { DocumentUpload } from "../workspace/DocumentUpload";
import type { Message } from "../../../../types/api";

interface CenterChatAreaProps {
  messages: readonly Message[];
  onSendMessage: (content: string) => Promise<void>;
  onUploadDocuments?: (files: FileList) => Promise<void>;
  loading?: boolean;
}

export function CenterChatArea({
  messages,
  onSendMessage,
  onUploadDocuments,
  loading = false,
}: CenterChatAreaProps) {
  const [showUploadSection, setShowUploadSection] = useState(false);

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Collapsible Upload Section */}
      {onUploadDocuments && (
        <div className="border-b border-gray-200 shrink-0">
          <button
            onClick={() => setShowUploadSection(!showUploadSection)}
            className="w-full flex items-center justify-between px-6 py-3 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">
                Document Upload
              </span>
              {loading && (
                <span className="text-xs text-blue-600">Uploading...</span>
              )}
            </div>
            {showUploadSection ? (
              <ChevronUp className="h-4 w-4 text-gray-600" />
            ) : (
              <ChevronDown className="h-4 w-4 text-gray-600" />
            )}
          </button>
          {showUploadSection && (
            <div className="px-6 pb-4">
              <DocumentUpload
                onUpload={onUploadDocuments}
                className="max-w-2xl mx-auto"
              />
            </div>
          )}
        </div>
      )}

      {/* Chat Panel - Takes remaining space */}
      <div className="flex-1 overflow-hidden">
        <ChatPanel
          messages={messages}
          onSendMessage={onSendMessage}
          loading={loading}
        />
      </div>
    </div>
  );
}
