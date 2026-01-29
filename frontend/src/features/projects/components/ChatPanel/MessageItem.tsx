import { Message } from "../../../../types/api";

interface MessageItemProps {
  readonly message: Message;
}

export function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === "user";

  return (
    <div className={`mb-4 ${isUser ? "text-right" : "text-left"}`}>
      <div
        className={`inline-block max-w-[80%] p-3 rounded-lg ${
          isUser ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-800"
        }`}
      >
        <div className="text-xs mb-1 opacity-75">{isUser ? "You" : "Assistant"}</div>
        <div className="whitespace-pre-wrap">{message.content}</div>
        {!isUser && message.kbSources !== undefined && message.kbSources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-300">
            <div className="text-xs font-semibold mb-2 text-gray-700">Sources:</div>
            <div className="space-y-1">
              {message.kbSources.map((source, index) => (
                // eslint-disable-next-line react/no-array-index-key
                <div key={index} className="text-xs">
                  <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                    {source.title} ({source.section})
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
