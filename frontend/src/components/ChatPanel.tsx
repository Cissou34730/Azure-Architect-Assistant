import { Message } from '../services/apiService';

interface ChatPanelProps {
  messages: Message[];
  chatInput: string;
  onChatInputChange: (input: string) => void;
  onSendMessage: (e: React.FormEvent) => void;
  loading: boolean;
  loadingMessage: string;
}

export function ChatPanel({
  messages,
  chatInput,
  onChatInputChange,
  onSendMessage,
  loading,
  loadingMessage,
}: ChatPanelProps) {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Clarification Chat</h2>
      
      {loading && loadingMessage && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md flex items-center gap-2">
          <svg className="animate-spin h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="text-sm text-blue-800">{loadingMessage}</span>
        </div>
      )}
      
      <div className="h-96 overflow-y-auto border border-gray-200 rounded-md p-4 mb-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`mb-4 ${
              msg.role === 'user' ? 'text-right' : 'text-left'
            }`}
          >
            <div
              className={`inline-block max-w-[80%] p-3 rounded-lg ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-800'
              }`}
            >
              <div className="text-xs mb-1 opacity-75">
                {msg.role === 'user' ? 'You' : 'Assistant'}
              </div>
              <div className="whitespace-pre-wrap">{msg.content}</div>
              {msg.role === 'assistant' && msg.wafSources && msg.wafSources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-300">
                  <div className="text-xs font-semibold mb-2">Sources (Azure Well-Architected Framework):</div>
                  <div className="space-y-1">
                    {msg.wafSources.map((source, idx) => (
                      <div key={idx} className="text-xs">
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          {source.title} ({source.section})
                        </a>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      
      <form onSubmit={onSendMessage} className="flex gap-2">
        <input
          type="text"
          value={chatInput}
          onChange={(e) => onChatInputChange(e.target.value)}
          placeholder="Ask a question or provide clarification..."
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !chatInput.trim()}
          className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
        >
          {loading ? (
            <>
              <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>Sending...</span>
            </>
          ) : 'Send'}
        </button>
      </form>
    </div>
  );
}
