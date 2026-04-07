export function KBLoadingScreen() {
  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand mx-auto mb-4" />
        <p className="text-secondary">Checking knowledge base status...</p>
      </div>
    </div>
  );
}

