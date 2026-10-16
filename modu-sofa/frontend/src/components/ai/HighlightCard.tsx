import { usePlayerStore } from '../../store/playerStore';
import type { Highlight } from '../../types/ai';
import { fmtTime } from '../../utils/format';
import { IconPlayFill } from '../common/Icons';

export function HighlightCard({ highlight: h }: { highlight: Highlight }) {
  const on = usePlayerStore((s) => s.currentTime >= h.start_time && s.currentTime < h.end_time);
  const playRange = usePlayerStore((s) => s.playRange);
  return (
    <button type="button" className={`hl-card${on ? ' on' : ''}`} onClick={() => playRange(h.start_time, h.end_time)}>
      <span style={{ display: 'flex', alignItems: 'center', gap: 10, width: '100%' }}>
        <span className="play-circle" aria-hidden="true">
          <IconPlayFill />
        </span>
        <span className="mono" style={{ fontSize: 14, color: 'var(--primary-ink)' }}>
          {fmtTime(h.start_time)}
        </span>
        <span style={{ flex: 1, fontWeight: 600 }}>{h.title}</span>
        <span className="mono xsmall muted">{fmtTime(h.end_time - h.start_time)}</span>
      </span>
      {/* 인용문은 Backend가 실제 Segment 텍스트로 만든 것 */}
      <span className="small" style={{ color: 'var(--ink-3)', paddingLeft: 42 }}>
        “{h.text}”
      </span>
    </button>
  );
}
