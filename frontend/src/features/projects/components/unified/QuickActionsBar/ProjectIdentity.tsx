import { Menu } from "lucide-react";

interface ProjectIdentityProps {
  readonly projectName: string;
  readonly onMenuClick?: () => void;
}

export function ProjectIdentity({
  projectName,
  onMenuClick,
}: ProjectIdentityProps) {
  return (
    <div className="flex items-center gap-4">
      {onMenuClick !== undefined && (
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 hover:bg-gray-100 rounded-lg transition-colors"
          title="Toggle menu"
          type="button"
        >
          <Menu className="h-5 w-5 text-gray-700" />
        </button>
      )}
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 rounded-lg bg-linear-to-br from-blue-500 to-blue-600 flex items-center justify-center shrink-0">
          <span className="text-white font-semibold text-sm">
            {projectName.charAt(0).toUpperCase()}
          </span>
        </div>
        <div>
          <h1 className="text-lg font-semibold text-gray-900 leading-tight">
            {projectName}
          </h1>
          <p className="text-xs text-gray-500">Architecture Workspace</p>
        </div>
      </div>
    </div>
  );
}
