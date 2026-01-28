import { ReactNode } from "react";
import { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon: iconComponent,
  title,
  description,
  action,
  className = "",
}: EmptyStateProps) {
   
  return (
    <div className={`flex flex-col items-center justify-center py-12 px-4 text-center ${className}`}>
      {iconComponent !== undefined && (
        <div className="mb-4 rounded-full bg-gray-100 p-3">
          {(() => {
            // eslint-disable-next-line @typescript-eslint/naming-convention
            const Icon = iconComponent;
            return <Icon className="h-8 w-8 text-gray-400" />;
          })()}
        </div>
      )}
      <h3 className="text-base font-semibold text-gray-900 mb-1">{title}</h3>
      {description !== undefined && description !== "" && (
        <p className="text-sm text-gray-600 max-w-md mb-4">{description}</p>
      )}
      {action !== undefined && action !== null && <div className="mt-2">{action}</div>}
    </div>
  );
}
