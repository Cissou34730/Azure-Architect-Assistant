import React from "react";

interface EmptyStateProps {
  readonly icon?: React.ReactNode;
  readonly message: string;
  readonly actionLabel?: string;
  readonly onClick?: () => void;
}

export function EmptyState({ icon, message, actionLabel, onClick }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-6 px-4 bg-surface/50 rounded-lg border border-dashed border-border">
      {icon !== undefined && icon}
      <p className="text-[11px] text-dim mt-2 mb-3">{message}</p>
      {actionLabel !== undefined && actionLabel !== "" && onClick !== undefined && (
        <button 
          onClick={onClick}
          className="text-[10px] font-bold text-brand hover:text-brand-strong uppercase tracking-widest border-b border-brand/30 pb-0.5"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}

