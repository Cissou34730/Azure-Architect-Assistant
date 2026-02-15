import { ReactNode } from "react";

type BadgeVariant = "default" | "primary" | "success" | "warning" | "error" | "info";
type BadgeSize = "sm" | "md" | "lg";

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  default: "ui-badge--default",
  primary: "ui-badge--primary",
  success: "ui-badge--success",
  warning: "ui-badge--warning",
  error: "ui-badge--error",
  info: "ui-badge--info",
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: "ui-badge--sm",
  md: "ui-badge--md",
  lg: "ui-badge--lg",
};

export function Badge({
  children,
  variant = "default",
  size = "md",
  className = "",
}: BadgeProps) {
  return (
    <span
      className={`ui-badge ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
    >
      {children}
    </span>
  );
}
