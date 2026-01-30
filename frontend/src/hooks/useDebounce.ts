import { useState, useEffect } from "react";

/**
 * A hook that returns a debounced value that only updates after a specified delay.
 * Useful for search inputs to avoid triggering expensive logic on every keystroke.
 *
 * @param value - The value to debounce
 * @param delay - The delay in milliseconds (default: 300)
 * @returns The debounced value
 */
export function useDebounce<T>(value: T, delay = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    // Set debouncedValue to value after delay
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    // Cleanup function to clear timeout if value or delay changes
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}
