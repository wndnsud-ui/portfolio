import { useEffect, useRef, useState } from 'react';
import { speakerName, type Speaker } from '../../types/speaker';
import { segmentText, type Segment } from '../../types/transcript';
import { fmtTime } from '../../utils/format';

interface Props {
  segment: Segment;
  speakers: Speaker[];
  onSave: (body: { edited_text?: string; speaker_id?: string }) => Promise<boolean>;
  onCancel: () => void;
}

export function SegmentEditForm({ segment, speakers, onSave, onCancel }: Props) {
  const [text, setText] = useState(segmentText(segment));
  const [speakerId, setSpeakerId] = useState(segment.speaker_id);
  const [busy, setBusy] = useState(false);
  const ta = useRef<HTMLTextAreaElement>(null);
  const current = speakers.find((s) => s.id === speakerId);

  useEffect(() => {
    ta.current?.focus();
    ta.current?.setSelectionRange(ta.current.value.length, ta.current.value.length);
  }, []);

  const save = async () => {
    const body: { edited_text?: string; speaker_id?: string } = {};
    if (text.trim() !== segmentText(segment)) body.edited_text = text;
    if (speakerId !== segment.speaker_id) body.speaker_id = speakerId;
    if (!Object.keys(body).length) return onCancel();
    setBusy(true);
    const ok = await onSave(body);
    setBusy(false);
    if (ok) onCancel();
  };

  return (
    <div className="seg-edit">
      <span className="seg-time" style={{ paddingTop: 8 }}>
        {fmtTime(segment.start_time)}
      </span>
      <label style={{ flex: 'none' }}>
        <span className="sr-only">화자</span>
        <select value={speakerId} onChange={(e) => setSpeakerId(e.target.value)} style={{ color: current?.color }}>
          {speakers.map((s) => (
            <option key={s.id} value={s.id}>
              {speakerName(s)}
            </option>
          ))}
        </select>
      </label>
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <label>
          <span className="sr-only">문장 수정</span>
          <textarea
            ref={ta}
            rows={2}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                void save();
              } else if (e.key === 'Escape') {
                e.preventDefault();
                onCancel();
              }
            }}
          />
        </label>
        <span className="xsmall muted">
          STT 원문 · <span style={{ color: 'var(--ink-3)' }}>{segment.original_text}</span>
        </span>
        <span style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
          <button type="button" className="btn btn-primary btn-sm" onClick={save} disabled={busy || !text.trim()}>
            저장
          </button>
          <button type="button" className="btn btn-sm" onClick={onCancel} disabled={busy}>
            취소
          </button>
          <span className="xsmall muted">원문은 지워지지 않아요. 고친 문장만 따로 저장돼요.</span>
        </span>
      </div>
    </div>
  );
}
