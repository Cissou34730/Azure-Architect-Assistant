/**
 * StatusBadge Component
 * Displays status with consistent styling
 */

import { ReactNode } from 'react';

export type StatusVariant = 
  | 'running' 
  | 'paused'
  | 'completed' 
  | 'failed' 
  | 'active' 
  | 'inactive';

interface StatusBadgeProps {
  variant: StatusVariant;
  children: ReactNode;
  pulse?: boolean;
}

const variantClasses: Record<StatusVariant, string> = {
  running: 'bg-status-running text-white',
  paused: 'bg-yellow-500 text-white',
  completed: 'bg-status-completed text-white',
  failed: 'bg-status-failed text-white',
  active: 'bg-accent-success text-white',
  inactive: 'bg-gray-100 text-gray-800',
};

export function StatusBadge({ variant, children, pulse = false }: StatusBadgeProps) {
  return (
    <span 
      className={`status-badge ${variantClasses[variant]} ${pulse ? 'animate-pulse' : ''}`}
      role="status"
      aria-label={`Status: ${variant}`}
    >
      {children}
    </span>
  );
}
