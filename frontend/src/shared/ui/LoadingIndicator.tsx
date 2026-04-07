export function LoadingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="ui-loading-indicator">
        <div className="flex items-center space-x-2">
          <div className="ui-loading-dot animation-delay-0" />
          <div className="ui-loading-dot animation-delay-150" />
          <div className="ui-loading-dot animation-delay-300" />
        </div>
      </div>
    </div>
  );
}
