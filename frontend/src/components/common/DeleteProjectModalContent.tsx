

interface DeleteProjectModalContentProps {
  readonly projectName: string;
}

export function DeleteProjectModalContent({ projectName }: DeleteProjectModalContentProps) {
  return (
    <div className="p-6">
      <p id="modal-description" className="text-sm text-gray-600 mb-4">
        Are you sure you want to delete{" "}
        <span className="font-semibold text-gray-900">{projectName}</span>?
      </p>
      <p className="text-sm text-gray-600 mb-4">
        This action cannot be undone. All project data, including:
      </p>
      <ul className="text-sm text-gray-600 list-disc list-inside space-y-1 mb-4">
        <li>Requirements and assumptions</li>
        <li>Architecture diagrams</li>
        <li>ADRs and cost estimates</li>
        <li>Chat messages and documents</li>
      </ul>
      <p className="text-sm text-red-600 font-medium">will be permanently deleted.</p>
    </div>
  );
}
