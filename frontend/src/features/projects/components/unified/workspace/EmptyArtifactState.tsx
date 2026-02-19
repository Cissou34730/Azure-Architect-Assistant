import { createElement } from "react";
import type { LucideIcon } from "lucide-react";

interface EmptyArtifactStateProps {
  readonly icon: LucideIcon;
  readonly title: string;
  readonly description: string;
}

export function EmptyArtifactState({
  icon,
  title,
  description,
}: EmptyArtifactStateProps) {
  const iconComponent = icon;
  return (
    <div className="h-full flex items-center justify-center">
      <div className="max-w-sm text-center space-y-3">
        <div className="mx-auto h-12 w-12 rounded-full bg-brand-soft flex items-center justify-center">
          {createElement(iconComponent, { className: "h-6 w-6 text-brand" })}
        </div>
        <div>
          <p className="text-sm font-semibold text-foreground">{title}</p>
          <p className="text-xs text-dim">{description}</p>
        </div>
        <p className="text-xs text-secondary">
          Open Inputs setup to upload documents and run analysis.
        </p>
      </div>
    </div>
  );
}


