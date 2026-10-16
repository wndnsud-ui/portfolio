import { memo, useState } from 'react';
import type { Speaker } from '../../types/speaker';
import { segmentText, type Segment } from '../../types/transcript';
import { fmtTime } from '../../utils/format';
import { IconPencil, IconTrash } from '../common/Icons';
import { SpeakerBadge } from './SpeakerBadge';

interface Props {
  segment: Segment;
  speaker: Speaker | undefined;
  active: boolean;
  /** 잘라낸 구간과 겹침: 'full'이면 내보낼 때 빠짐 */
  cut?: 'full' | 'partial' | null;
  /** 편집 모드에서 문장 선택 (클릭 대신) */
  onPick?: (start: number, end: number, extend: boolean) => void;
  selected?: boolean;
  onSeek: (t: number) => void;
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
  onRestore: (id: string) => void;
  onRevert: (id: string) => void;
}

export const TranscriptLine = memo(function TranscriptLine({
  segment: s,
  speaker,
  active,
  cut = null,
  onPick,
  selected = false,
  onSeek,
  onEdit,
  onDelete,
  onRestore,
  onRevert,
}: Props) {
  const [showOriginal, setShowOriginal] = useState(false);

  if (s.is_deleted) {
    // MVP에서는 오디오를 자르지 않으므로 재생은 그대로 진행된다
    return (
      <li data-seg-id={s.id}>
        <div className="seg-deleted" style={active ? { boxShadow: 'inset 0 0 0 1px #CFC4FF' } : undefined}>
          <span className="seg-time" style={{ color: '#8A88A0' }}>
            {fmtTime(s.start_time)}
          </span>
          <span className="seg-spk small" style={{ color: 'var(--faint)', paddingTop: 3 }}>
            {speaker ? speaker.display_name ?? speaker.speaker_code : ''}
          </span>
          <span style={{ flex: '1 1 auto', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
            <s>{segmentText(s)}</s>
            <span className="xsmall" style={{ color: 'var(--faint)' }}>
              삭제됨 · 오디오에는 그대로 남아 있어요
            </span>
          </span>
          <button type="button" className="btn btn-xs" onClick={() => onRestore(s.id)}>
            복원
          </button>
        </div>
      </li>
    );
  }

  const edited = s.edited_text !== null;
  return (
    <li data-seg-id={s.id}>
      <div className={`seg-row${active ? ' active' : ''}${cut === 'full' ? ' seg-cut' : ''}${selected ? ' seg-selected' : ''}`}>
        <button
          type="button"
          className="seg-main"
          onClick={(e) => (onPick ? onPick(s.start_time, s.end_time, e.shiftKey) : onSeek(s.start_time))}
          onDoubleClick={() => onEdit(s.id)}
          aria-current={active ? 'true' : undefined}
          aria-label={`${fmtTime(s.start_time)}부터 재생: ${segmentText(s)}`}
        >
          <span className="seg-time">{fmtTime(s.start_time)}</span>
          <span className="seg-spk">
            <SpeakerBadge speaker={speaker} />
          </span>
          <span className="seg-text">{segmentText(s)}</span>
          {cut && <span className="cut-tag">{cut === 'full' ? '잘림' : '일부 잘림'}</span>}
        </button>
        <span className="seg-actions">
          <button type="button" className="icon-btn icon-btn-sm" aria-label="문장 수정" title="문장 수정" onClick={() => onEdit(s.id)}>
            <IconPencil />
          </button>
          <button type="button" className="icon-btn icon-btn-sm" aria-label="문장 삭제" title="문장 삭제" onClick={() => onDelete(s.id)}>
            <IconTrash />
          </button>
        </span>
      </div>
      {edited && (
        <div className="edited-meta">
          <span style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
            <span className="edited-tag">수정됨</span>
            <button type="button" className="btn-link" style={{ height: 28 }} aria-expanded={showOriginal} onClick={() => setShowOriginal((v) => !v)}>
              {showOriginal ? '원문 숨기기' : '원문 보기'}
            </button>
          </span>
          {showOriginal && (
            <span className="orig-box">
              {s.original_text}{' '}
              <button type="button" className="btn-link" onClick={() => onRevert(s.id)}>
                원문으로 되돌리기
              </button>
            </span>
          )}
        </div>
      )}
    </li>
  );
});
