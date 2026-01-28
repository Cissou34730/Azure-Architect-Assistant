export function ProjectOverviewEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="text-center max-w-md">
        <div className="mb-4 rounded-full bg-blue-50 p-6 inline-block">
          <svg
            className="h-16 w-16 text-blue-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        </div>
        <h3 className="text-xl font-semibold text-gray-900 mb-2">Get Started</h3>
        <p className="text-gray-600 mb-6">
          Upload and analyze documents in the Workspace to start building your architecture.
        </p>
        <button
          onClick={() => {
            const event = new CustomEvent("navigate-to-workspace");
            window.dispatchEvent(event);
          }}
          className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          Go to Workspace
        </button>
      </div>
    </div>
  );
}
