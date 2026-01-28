import React from "react";

interface ActionButtonProps {
  readonly icon: React.ComponentType<{ readonly className?: string }>;
  readonly label: string;
  readonly onClick: () => void;
  readonly shortcut?: string;
  readonly showTooltip?: boolean;
  readonly variant?: "default" | "primary";
}

export function ActionButton({
  icon: Icon, // eslint-disable-line @typescript-eslint/naming-convention
  label,
  onClick,
  shortcut,
  showTooltip,
  variant = "default",
}: ActionButtonProps) {
  const baseClasses = "flex items-center gap-2 px-4 py-2 rounded-lg transition-all font-medium text-sm";
  const variantClasses =
    variant === "primary"
      ? "bg-blue-600 text-white hover:bg-blue-700 shadow-sm"
      : "bg-gray-100 text-gray-700 hover:bg-gray-200";

  return (
    <button
      onClick={onClick}
      className={`${baseClasses} ${variantClasses}`}
      title={showTooltip === true && shortcut !== undefined ? `${label} (${shortcut})` : label}
      type="button"
    >
      <Icon className="h-4 w-4" />
      <span className="hidden lg:inline">{label}</span>
      {shortcut !== undefined && (
        <kbd className="hidden xl:inline-block px-1.5 py-0.5 bg-white/10 border border-white/20 rounded text-xs">
          {shortcut}
        </kbd>
      )}
    </button>
  );
}
