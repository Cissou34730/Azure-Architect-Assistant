import { useRef, useEffect } from "react";

/**
 * A hook that tracks and logs the number of times a component has rendered.
 * Only logs in development mode.
 *
 * @param componentName Unique name for the component being tracked
 */
export function useRenderCount(componentName: string) {
  const count = useRef(0);

  useEffect(() => {
    count.current += 1;
    if (import.meta.env.DEV) {
      console.log(`[Render] ${componentName}: ${count.current}`);
    }
  });

  return count.current;
}
