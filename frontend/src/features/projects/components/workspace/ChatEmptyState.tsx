export function ChatEmptyStateComp() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
      <svg
        className="h-16 w-16 mb-4 text-gray-300"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
        />
      </svg>
      <p className="text-lg font-medium text-gray-700 mb-2">
        Start a conversation
      </p>
      <p className="text-sm text-gray-500 max-w-md">
        Ask me to analyze documents, generate architecture candidates, create
        ADRs, or answer Azure questions.
      </p>
    </div>
  );
}
