/**
 * Button Component
 * Reusable button with consistent styling and accessibility
 */

import { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant =
  | "primary"
  | "secondary"
  | "success"
  | "warning"
  | "danger"
  | "ghost";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  children: ReactNode;
  isLoading?: boolean;
  icon?: ReactNode;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: "ui-btn--primary",
  secondary: "ui-btn--secondary",
  success: "ui-btn--success",
  warning: "ui-btn--warning",
  danger: "ui-btn--danger",
  ghost: "ui-btn--ghost",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "ui-btn--sm",
  md: "ui-btn--md",
  lg: "ui-btn--lg",
};

function LoadingSpinner() {
  return (
    <>
      <svg
        className="animate-spin h-4 w-4"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      <span>Loading...</span>
    </>
  );
}

export function Button({
  variant = "primary",
  size = "md",
  children,
  isLoading = false,
  icon,
  disabled,
  className = "",
  ...props
}: ButtonProps) {
  const baseClasses = "ui-btn";
  const classes = `${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`;

  const isActuallyDisabled = (disabled ?? false) || isLoading;

  return (
    <button
      className={classes}
      disabled={isActuallyDisabled}
      aria-busy={isLoading ? "true" : "false"}
      {...props}
    >
      {isLoading ? (
        <LoadingSpinner />
      ) : (
        <>
          {Boolean(icon) && <span aria-hidden="true">{icon}</span>}
          {children}
        </>
      )}
    </button>
  );
}
