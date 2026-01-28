import React from "react";

interface EmptyStateProps {
  readonly icon?: React.ReactNode;
  readonly message: string;
  readonly actionLabel?: string;
  readonly onClick?: () => void;
}

export function EmptyState({ icon, message, actionLabel, onClick }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-6 px-4 bg-gray-50/50 rounded-lg border border-dashed border-gray-200">
      {icon !== undefined && icon}
      <p className="text-[11px] text-gray-500 mt-2 mb-3">{message}</p>
      {actionLabel !== undefined && actionLabel !== "" && onClick !== undefined && (
        <button 
          onClick={onClick}
          className="text-[10px] font-bold text-blue-600 hover:text-blue-700 uppercase tracking-widest border-b border-blue-600/30 pb-0.5"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
