import { useState, useEffect, useRef, type RefObject } from "react";

interface UseIntersectionObserverProps {
  root?: Element | null;
  rootMargin?: string;
  threshold?: number | number[];
  freezeOnceVisible?: boolean;
}

export function useIntersectionObserver<T extends Element = Element>({
  root = null,
  rootMargin = "50px",
  threshold = 0.1,
  freezeOnceVisible = false,
}: UseIntersectionObserverProps = {}): {
  ref: RefObject<T | null>;
  isVisible: boolean;
  hasBeenVisible: boolean;
} {
  const ref = useRef<T | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const [hasBeenVisible, setHasBeenVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (node === null) return;

    if (freezeOnceVisible && hasBeenVisible) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        const visible = entry.isIntersecting;
        setIsVisible(visible);

        if (visible && !hasBeenVisible) {
          setHasBeenVisible(true);
        }
      },
      { root, rootMargin, threshold },
    );

    observer.observe(node);

    return () => {
      observer.disconnect();
    };
  }, [root, rootMargin, threshold, freezeOnceVisible, hasBeenVisible]);

  return { ref, isVisible, hasBeenVisible };
}
