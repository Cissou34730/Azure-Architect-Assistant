import { useRef, useEffect } from "react";

/**
 * Hook to keep a reference to a callback updated without triggering re-effects
 */
export function useCallbackRef<T>(callback: T | undefined) {
  const ref = useRef<T | undefined>(callback);

  useEffect(() => {
    ref.current = callback;
  }, [callback]);

  return ref;
}
