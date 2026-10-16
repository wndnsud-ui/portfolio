import type { Chapter } from '../../types/ai';
import { fmtTime } from '../../utils/format';

interface Props {
  chapters: Chapter[];
  onSeek: (t: number) => void;
  /** 트랜스크립트 패널의 챕터 탭에서는 카드형 + 문장 번호 표시 */
  variant?: 'compact' | 'full';
  segSeq?: Map<string, number>;
  activeId?: string | null;
}

export function ChapterList({ chapters, onSeek, variant = 'compact', segSeq, activeId }: Props) {
  if (!chapters.length) return <p className="small muted">챕터가 아직 없어요.</p>;

  if (variant === 'full') {
    return (
      <ol style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {chapters.map((c) => (
          <li key={c.id}>
            <button type="button" className={`list-btn${c.id === activeId ? ' on' : ''}`} onClick={() => onSeek(c.start_time)}>
              <span className="mono" style={{ fontSize: 14, color: 'var(--primary-ink)', width: 56 }}>
                {fmtTime(c.start_time)}
              </span>
              <span style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
                <span style={{ fontWeight: 600, fontSize: 15 }}>{c.title}</span>
                {c.description && <span className="small muted">{c.description}</span>}
              </span>
              {segSeq?.get(c.start_segment_id) != null && (
                <span className="xsmall muted">문장 #{segSeq.get(c.start_segment_id)}부터</span>
              )}
            </button>
          </li>
        ))}
      </ol>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <p className="small muted" style={{ marginBottom: 4 }}>
        모든 시간은 실제 문장 위치 기준이에요.
      </p>
      {chapters.map((c) => (
        <button key={c.id} type="button" className="ghost-row" onClick={() => onSeek(c.start_time)}>
          <span className="mono small" style={{ color: 'var(--primary-ink)', width: 48 }}>
            {fmtTime(c.start_time)}
          </span>
          <span style={{ fontWeight: 500 }}>{c.title}</span>
        </button>
      ))}
    </div>
  );
}
