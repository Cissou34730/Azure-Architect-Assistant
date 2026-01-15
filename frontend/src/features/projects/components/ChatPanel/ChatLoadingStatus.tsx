import { LoadingSpinner } from "../../../../components/common";

interface ChatLoadingStatusProps {
  readonly loading: boolean;
  readonly message: string;
}

export function ChatLoadingStatus({ loading, message }: ChatLoadingStatusProps) {
  if (!loading || message === "") {
    return null;
  }

  return (
    <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md flex items-center gap-2">
      <LoadingSpinner size="sm" />
      <span className="text-sm text-blue-800">{message}</span>
    </div>
  );
}
