import { useEffect, useState } from 'react';
import { useEditStore } from '../../store/editStore';
import { useEpisodeStore } from '../../store/episodeStore';
import { usePlayerStore } from '../../store/playerStore';
import {
  cutSelection,
  fmtPrecise,
  keepOnly,
  normalize,
  parseTime,
  restoreSelection,
  snapToSegments,
  totalLength,
  type Range,
} from '../../utils/editOps';
import { fmtTime } from '../../utils/format';

interface Props {
  duration: number;
  skip: boolean;
  onSkipChange: (v: boolean) => void;
}

const ZOOMS = [
  { v: 0, label: '전체' },
  { v: 10, label: '2배' },
  { v: 30, label: '5배' },
  { v: 80, label: '10배' },
  { v: 200, label: '최대' },
];

/** 시각 입력 + ±0.1초 미세 조정 */
function TimeField({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  const [text, setText] = useState(fmtPrecise(value));
  useEffect(() => setText(fmtPrecise(value)), [value]);
  const commit = () => {
    const v = parseTime(text);
    if (v == null) setText(fmtPrecise(value));
    else onChange(v);
  };
  return (
    <span className="time-field">
      <button type="button" aria-label={`${label} 0.1초 앞으로`} onClick={() => onChange(value - 0.1)}>
        −
      </button>
      <label>
        <span className="sr-only">{label}</span>
        <input
          className="mono"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()}
          aria-label={label}
        />
      </label>
      <button type="button" aria-label={`${label} 0.1초 뒤로`} onClick={() => onChange(value + 0.1)}>
        +
      </button>
    </span>
  );
}

export function EditBar({ duration, skip, onSkipChange }: Props) {
  const cuts = useEpisodeStore((s) => s.cuts);
  const segments = useEpisodeStore((s) => s.segments);
  const { selection, setSelection, apply, undo, redo, undoStack, redoStack, zoom, setZoom, setActive } = useEditStore();
  const playRange = usePlayerStore((s) => s.playRange);

  const setSel = (patch: Partial<Range>) => {
    if (!selection) return;
    const next = { ...selection, ...patch };
    next.start_time = Math.max(0, Math.min(next.start_time, duration));
    next.end_time = Math.max(0, Math.min(next.end_time, duration));
    if (next.end_time > next.start_time) setSelection(next);
  };

  const doCut = () => selection && (apply(cutSelection(cuts, selection, duration)), setSelection(null));
  const doKeep = () => selection && (apply(keepOnly(cuts, selection, duration)), setSelection(null));
  const doRestore = () => selection && (apply(restoreSelection(cuts, selection, duration)), setSelection(null));
  const deleted = segments.filter((s) => s.is_deleted).map((s) => ({ start_time: s.start_time, end_time: s.end_time }));
  const pendingDeleted = deleted.filter((d) => !cuts.some((c) => c.start_time <= d.start_time + 0.05 && c.end_time >= d.end_time - 0.05));

  // 단축키: Delete = 선택 삭제, Ctrl+Z / Ctrl+Shift+Z(또는 Ctrl+Y) = 되돌리기 / 다시하기, Esc = 선택 해제
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      if (el.closest('input, textarea, select, [contenteditable="true"]')) return;
      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        if (e.shiftKey) redo();
        else undo();
      } else if (mod && e.key.toLowerCase() === 'y') {
        e.preventDefault();
        redo();
      } else if ((e.key === 'Delete' || e.key === 'Backspace') && useEditStore.getState().selection) {
        e.preventDefault();
        doCut();
      } else if (e.key === 'Escape') {
        setSelection(null);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  return (
    <div className="cut-bar" role="region" aria-label="편집">
      <div className="cut-bar-head">
        <span style={{ fontWeight: 700 }}>편집</span>
        <span className="small muted">파형을 드래그하거나 문장을 클릭(Shift+클릭으로 범위)해 구간을 고르세요.</span>
        <span style={{ flex: 1 }} />
        <button type="button" className="btn btn-xs" onClick={undo} disabled={!undoStack.length} title="되돌리기 (Ctrl+Z)">
          되돌리기
        </button>
        <button type="button" className="btn btn-xs" onClick={redo} disabled={!redoStack.length} title="다시하기 (Ctrl+Shift+Z)">
          다시하기
        </button>
        <label className="small select-wrap" style={{ height: 32 }}>
          확대
          <select value={zoom} onChange={(e) => setZoom(Number(e.target.value))}>
            {ZOOMS.map((z) => (
              <option key={z.v} value={z.v}>
                {z.label}
              </option>
            ))}
          </select>
        </label>
        <label className="small" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <input type="checkbox" checked={skip} onChange={(e) => onSkipChange(e.target.checked)} />
          잘린 구간 건너뛰며 듣기
        </label>
        <button type="button" className="btn btn-primary btn-sm" onClick={() => setActive(false)}>
          완료
        </button>
      </div>

      {selection ? (
        <div className="sel-row">
          <span className="sel-label">선택</span>
          <TimeField label="선택 시작" value={selection.start_time} onChange={(v) => setSel({ start_time: v })} />
          <span className="muted">~</span>
          <TimeField label="선택 끝" value={selection.end_time} onChange={(v) => setSel({ end_time: v })} />
          <span className="small muted mono">({(selection.end_time - selection.start_time).toFixed(1)}초)</span>
          <button type="button" className="btn btn-xs" onClick={() => setSelection(snapToSegments(selection, segments))} title="시작·끝을 문장 경계에 맞춰요">
            문장에 맞추기
          </button>
          <button type="button" className="btn btn-xs" onClick={() => playRange(selection.start_time, selection.end_time)}>
            ▶ 선택 듣기
          </button>
          <span style={{ flex: 1 }} />
          <button type="button" className="btn btn-danger btn-sm" onClick={doCut} title="Delete">
            이 구간 삭제
          </button>
          <button type="button" className="btn btn-sm sel-keep" onClick={doKeep}>
            여기만 살리기
          </button>
          <button
            type="button"
            className="btn btn-sm"
            onClick={doRestore}
            disabled={!cuts.some((c) => c.end_time > selection.start_time && c.start_time < selection.end_time)}
          >
            되살리기
          </button>
          <button type="button" className="btn-link" onClick={() => setSelection(null)}>
            선택 해제
          </button>
        </div>
      ) : null}

      <div className="cut-list">
        {cuts.length > 0 ? (
          <>
            <span className="small" style={{ color: 'var(--danger-ink)', fontWeight: 600 }}>
              잘린 구간 {cuts.length}개 · 총 {fmtTime(totalLength(cuts))} · 결과 {fmtTime(duration - totalLength(cuts))}
            </span>
            {cuts.map((c, i) => (
              <span key={`${c.start_time}-${i}`} className="cut-chip">
                <button type="button" className="mono" onClick={() => setSelection({ ...c })} title="이 구간 선택">
                  {fmtPrecise(c.start_time)}~{fmtPrecise(c.end_time)}
                </button>
                <button
                  type="button"
                  aria-label={`${fmtTime(c.start_time)}~${fmtTime(c.end_time)} 구간 되살리기`}
                  onClick={() => apply(cuts.filter((_, j) => j !== i))}
                >
                  ✕
                </button>
              </span>
            ))}
            <button type="button" className="btn-link" onClick={() => apply([])}>
              모두 되살리기
            </button>
          </>
        ) : (
          <span className="small muted">아직 잘린 구간이 없어요. 원본은 그대로 두고 내보낼 때만 잘라요.</span>
        )}
        {pendingDeleted.length > 0 && (
          <button type="button" className="btn btn-xs" onClick={() => apply(normalize([...cuts, ...pendingDeleted], duration))}>
            대본에서 삭제한 문장 {pendingDeleted.length}개도 자르기
          </button>
        )}
      </div>
    </div>
  );
}
