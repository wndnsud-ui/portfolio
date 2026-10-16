import { IconCheck } from '../common/Icons';

interface Props {
  candidates: string[];
  current: string | null;
  onPick: (title: string) => void;
}

export function TitleSuggestions({ candidates, current, onPick }: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <p className="small muted">선택한 제목만 에피소드에 저장돼요.</p>
      {candidates.map((t, i) => {
        const on = current === t;
        return (
          <button
            key={t}
            type="button"
            className={`list-btn${on ? ' on' : ''}`}
            style={{ gap: 12, padding: '12px 14px', fontSize: 14, fontWeight: on ? 600 : 400 }}
            aria-pressed={on}
            onClick={() => onPick(t)}
          >
            <span className="mono xsmall muted">{String(i + 1).padStart(2, '0')}</span>
            <span style={{ flex: 1 }}>{t}</span>
            {on && <IconCheck stroke="#4A2FD0" strokeWidth={2.4} />}
          </button>
        );
      })}
    </div>
  );
}
