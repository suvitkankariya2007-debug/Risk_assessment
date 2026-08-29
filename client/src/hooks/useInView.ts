import { useEffect, useRef, useState } from "react";

/**
 * Returns true when the referenced element is visible in the viewport.
 * Uses IntersectionObserver with a configurable threshold.
 */
export function useInView(
  options?: IntersectionObserverInit
): [React.RefObject<HTMLElement | null>, boolean] {
  const ref = useRef<HTMLElement | null>(null);
  const [isInView, setIsInView] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.unobserve(element);
        }
      },
      { threshold: 0.3, ...options }
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return [ref, isInView];
}
