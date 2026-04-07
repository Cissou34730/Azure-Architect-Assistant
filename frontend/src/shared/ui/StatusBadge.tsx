/**
 * StatusBadge Component
 * Displays status with consistent styling
 */

import { ReactNode } from "react";

type StatusVariant =
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "active"
  | "inactive";

interface StatusBadgeProps {
  variant: StatusVariant;
  children: ReactNode;
  pulse?: boolean;
}

const variantClasses: Record<StatusVariant, string> = {
  running: "ui-status-running",
  paused: "ui-status-paused",
  completed: "ui-status-completed",
  failed: "ui-status-failed",
  active: "ui-status-active",
  inactive: "ui-status-inactive",
};

export function StatusBadge({
  variant,
  children,
  pulse = false,
}: StatusBadgeProps) {
  return (
    <span
      className={`status-badge ${variantClasses[variant]} ${pulse ? "animate-pulse" : ""}`}
      role="status"
      aria-label={`Status: ${variant}`}
    >
      {children}
    </span>
  );
}
