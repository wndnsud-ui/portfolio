import { useEffect, useRef } from 'react';

/** active일 때 interval(기본 4초)마다 tick을 호출한다. 탭이 숨겨져 있으면 건너뛴다. */
export function useEpisodePolling(active: boolean, tick: () => unknown, intervalMs = 4000) {
  const ref = useRef(tick);
  ref.current = tick;

  useEffect(() => {
    if (!active) return;
    const id = window.setInterval(() => {
      if (document.visibilityState === 'visible') void ref.current();
    }, intervalMs);
    return () => window.clearInterval(id);
  }, [active, intervalMs]);
}
