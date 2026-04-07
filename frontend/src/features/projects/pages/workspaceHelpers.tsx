export function ProjectNotFound() {
  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <h2 className="text-xl font-semibold text-foreground mb-2">Project not found</h2>
        <p className="text-secondary">The requested project could not be loaded.</p>
      </div>
    </div>
  );
}

export function ProjectLoading() {
  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand mx-auto mb-4" />
        <p className="text-secondary">Loading project...</p>
      </div>
    </div>
  );
}
