import { memo, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

interface MessageContentProps {
  content: string;
  isUser: boolean;
}

// eslint-disable-next-line react-refresh/only-export-components -- Memoized component export pattern
function MessageContentInner({ content, isUser }: MessageContentProps) {
  const markdownComponents = useMemo<Components>(
    () => ({
      code({ className, children }) {
        const match = /language-(\w+)/.exec(className ?? "");
        const isInline = match === null;
        
        let contentStr = "";
        if (typeof children === "string") {
          contentStr = children;
        } else if (Array.isArray(children)) {
          contentStr = children
            .map((child) => (typeof child === "string" ? child : ""))
            .join("");
        }
        
        const code = contentStr.replace(/\n$/, "");

        if (!isInline) {
          return (
            <SyntaxHighlighter style={oneDark} language={match[1]} PreTag="div">
              {code}
            </SyntaxHighlighter>
          );
        }

        return <code className={className ?? ""}>{children}</code>;
      },
      p({ children }) {
        return <p>{children}</p>;
      },
    }),
    [],
  );

  if (isUser) {
    return <p className="text-sm whitespace-pre-wrap">{content}</p>;
  }

  return (
    <div className="prose prose-sm max-w-none prose-pre:bg-code-bg prose-pre:text-code-fg">
      <ReactMarkdown components={markdownComponents}>{content}</ReactMarkdown>
    </div>
  );
}

export const messageContentComp = memo(MessageContentInner);

