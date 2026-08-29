import { useEffect, useState } from "react";

/**
 * Animates a number from 0 to a target value over a given duration.
 * Supports both integer and decimal targets (auto-detects from target string).
 */
export function useCountUp(
  target: number,
  duration: number = 900,
  enabled: boolean = true
): number {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!enabled) {
      setValue(0);
      return;
    }

    let start = 0;
    const startTime = performance.now();

    function tick(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // easeOutExpo
      const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      setValue(start + (target - start) * eased);
      if (progress < 1) {
        requestAnimationFrame(tick);
      }
    }

    requestAnimationFrame(tick);
  }, [target, duration, enabled]);

  return value;
}
