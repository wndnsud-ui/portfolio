import { useEffect, useMemo, useRef } from 'react';
import { usePlayerStore } from '../store/playerStore';
import type { Segment } from '../types/transcript';
import { findActiveSegment } from '../utils/findActiveSegment';

const USER_SCROLL_PAUSE_MS = 4000;

/**
 * 재생 위치에 맞는 현재 문장 id를 돌려주고, 화면 밖이면 자동 스크롤한다.
 * 사용자가 직접 스크롤하는 동안에는 자동 스크롤을 잠시 멈춘다.
 */
export function useTranscriptSync(segments: Segment[], scrollRoot: HTMLElement | null) {
  const starts = useMemo(() => segments.map((s) => s.start_time), [segments]);
  const activeIdx = usePlayerStore((s) => findActiveSegment(starts, s.currentTime));
  const activeId = activeIdx >= 0 ? segments[activeIdx]?.id ?? null : null;
  const userScrollAt = useRef(0);

  useEffect(() => {
    if (!scrollRoot) return;
    const mark = () => {
      userScrollAt.current = Date.now();
    };
    const onKey = (e: KeyboardEvent) => {
      if (['PageUp', 'PageDown', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(e.key)) mark();
    };
    scrollRoot.addEventListener('wheel', mark, { passive: true });
    scrollRoot.addEventListener('touchmove', mark, { passive: true });
    scrollRoot.addEventListener('keydown', onKey);
    return () => {
      scrollRoot.removeEventListener('wheel', mark);
      scrollRoot.removeEventListener('touchmove', mark);
      scrollRoot.removeEventListener('keydown', onKey);
    };
  }, [scrollRoot]);

  useEffect(() => {
    if (!activeId || !scrollRoot) return;
    if (Date.now() - userScrollAt.current < USER_SCROLL_PAUSE_MS) return;
    const el = scrollRoot.querySelector<HTMLElement>(`[data-seg-id="${activeId}"]`);
    if (!el) return;
    const root = scrollRoot.getBoundingClientRect();
    const r = el.getBoundingClientRect();
    if (r.top < root.top + 8 || r.bottom > root.bottom - 8) {
      el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
  }, [activeId, scrollRoot]);

  return activeId;
}
