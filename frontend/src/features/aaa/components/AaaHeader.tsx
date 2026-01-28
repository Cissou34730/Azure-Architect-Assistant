interface AaaHeaderProps {
  readonly loading: boolean;
  readonly loadingMessage: string | undefined;
}

export function AaaHeader({ loading, loadingMessage }: AaaHeaderProps) {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-1">AAA Workspace</h2>
      <p className="text-sm text-gray-600">
        Upload/analyze project documents and review extracted requirements.
      </p>
      {loading && (
        <p className="text-sm text-gray-600 mt-2">
          {loadingMessage !== "" && loadingMessage !== undefined
            ? loadingMessage
            : "Working..."}
        </p>
      )}
    </div>
  );
}
