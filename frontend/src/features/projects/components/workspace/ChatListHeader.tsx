import { Loader2 } from "lucide-react";

interface ChatHeaderProps {
  readonly canLoadOlder: boolean;
  readonly loadingOlder: boolean;
  readonly onLoadOlder: () => void;
}

export function ChatListHeader({ canLoadOlder, loadingOlder, onLoadOlder }: ChatHeaderProps) {
  if (!canLoadOlder) return null;

  return (
    <div className="p-4 text-center">
      <button
        type="button"
        onClick={onLoadOlder}
        disabled={loadingOlder}
        className="text-sm font-medium text-brand hover:text-brand-strong disabled:text-dim disabled:cursor-not-allowed flex items-center justify-center gap-2 mx-auto"
      >
        {loadingOlder ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading older messages...
          </>
        ) : (
          "Load older messages"
        )}
      </button>
    </div>
  );
}
