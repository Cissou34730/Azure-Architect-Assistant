import { createElement } from "react";
import type { LucideIcon } from "lucide-react";

interface EmptyArtifactStateProps {
  readonly icon: LucideIcon;
  readonly title: string;
  readonly description: string;
  readonly onGenerate: () => Promise<void>;
  readonly loading: boolean;
}

export function EmptyArtifactState({
  icon,
  title,
  description,
  onGenerate,
  loading,
}: EmptyArtifactStateProps) {
  const iconComponent = icon;
  return (
    <div className="h-full flex items-center justify-center">
      <div className="max-w-sm text-center space-y-3">
        <div className="mx-auto h-12 w-12 rounded-full bg-blue-50 flex items-center justify-center">
          {createElement(iconComponent, { className: "h-6 w-6 text-blue-600" })}
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-900">{title}</p>
          <p className="text-xs text-gray-500">{description}</p>
        </div>
        <button
          type="button"
          onClick={() => { void onGenerate(); }}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
        >
          Generate Analysis
        </button>
      </div>
    </div>
  );
}
