/**
 * LoadingSpinner Component
 * Reusable loading indicator with accessibility
 */

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  message?: string;
}

const sizeClasses = {
  sm: 'h-6 w-6',
  md: 'h-12 w-12',
  lg: 'h-16 w-16',
};

export function LoadingSpinner({ size = 'md', message }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4" role="status" aria-live="polite">
      <div 
        className={`animate-spin rounded-pill border-b-2 border-accent-primary ${sizeClasses[size]}`}
        aria-hidden="true"
      />
      {message && (
        <p className="text-sm text-gray-600">{message}</p>
      )}
      <span className="sr-only">Loading...</span>
    </div>
  );
}
