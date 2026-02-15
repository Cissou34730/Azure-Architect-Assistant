import { useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import { Project } from "../../types/api";
import { DeleteProjectModalContent } from "./DeleteProjectModalContent";

interface DeleteProjectModalProps {
  readonly project: Project;
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly onConfirm: () => Promise<void>;
}

export function DeleteProjectModal({
  project,
  isOpen,
  onClose,
  onConfirm,
}: DeleteProjectModalProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    setIsDeleting(true);
    setError(null);
    try {
      await onConfirm();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete project");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      onClose();
    } else if (e.key === "Enter" && !isDeleting) {
      void handleConfirm();
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-overlay/50 z-50 animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* Modal */}
      <div
        className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-card rounded-lg shadow-xl z-50 animate-in fade-in zoom-in-95 duration-200"
        onKeyDown={handleKeyDown}
        role="dialog"
        aria-labelledby="modal-title"
        aria-describedby="modal-description"
      >
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-danger-soft flex items-center justify-center">
              <AlertTriangle className="h-5 w-5 text-danger" />
            </div>
            <h2 id="modal-title" className="text-lg font-semibold text-foreground">
              Delete Project
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-dim hover:text-secondary transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <DeleteProjectModalContent projectName={project.name} />
        
        <div className="px-6 pb-6">
          {error !== null && error !== "" && (
            <div className="p-3 bg-danger-soft border border-danger-line rounded-lg">
              <p className="text-sm text-danger-strong">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-border">
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="px-4 py-2 text-sm font-medium text-secondary bg-card border border-border-stronger rounded-lg hover:bg-surface disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={isDeleting}
            className="px-4 py-2 text-sm font-medium text-inverse bg-danger rounded-lg hover:bg-danger-strong disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {isDeleting ? (
              <>
                <div className="w-4 h-4 border-2 border-inverse border-t-transparent rounded-full animate-spin" />
                Deleting...
              </>
            ) : (
              "Delete Project"
            )}
          </button>
        </div>
      </div>
    </>
  );
}



