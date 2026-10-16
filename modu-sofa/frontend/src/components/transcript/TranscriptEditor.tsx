import { useCallback, useMemo, useState } from 'react';
import { useTranscriptSync } from '../../hooks/useTranscriptSync';
import { useEditStore } from '../../store/editStore';
import { useEpisodeStore } from '../../store/episodeStore';
import { usePlayerStore } from '../../store/playerStore';
import { speakerName } from '../../types/speaker';
import { cutCoverage } from '../../types/edit';
import { segmentText } from '../../types/transcript';
import { IconSearch } from '../common/Icons';
import { SegmentEditForm } from './SegmentEditForm';
import { TranscriptLine } from './TranscriptLine';

export function TranscriptEditor({ scrollRoot }: { scrollRoot: HTMLElement | null }) {
  const segments = useEpisodeStore((s) => s.segments);
  const cuts = useEpisodeStore((s) => s.cuts);
  const speakers = useEpisodeStore((s) => s.speakers);
  const updateSegment = useEpisodeStore((s) => s.updateSegment);
  const revertSegment = useEpisodeStore((s) => s.revertSegment);
  const deleteSegment = useEpisodeStore((s) => s.deleteSegment);
  const restoreSegment = useEpisodeStore((s) => s.restoreSegment);
  const seek = usePlayerStore((s) => s.seek);
  const editMode = useEditStore((s) => s.active);
  const selection = useEditStore((s) => s.selection);

  const [query, setQuery] = useState('');
  const [speakerFilter, setSpeakerFilter] = useState('all');
  const [editingId, setEditingId] = useState<string | null>(null);

  const activeId = useTranscriptSync(segments, scrollRoot);
  const speakerById = useMemo(() => new Map(speakers.map((s) => [s.id, s])), [speakers]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return segments.filter(
      (s) =>
        (speakerFilter === 'all' || s.speaker_id === speakerFilter) &&
        (!q || segmentText(s).toLowerCase().includes(q) || s.original_text.toLowerCase().includes(q)),
    );
  }, [segments, query, speakerFilter]);

  const onSeek = useCallback((t: number) => seek(t), [seek]);
  /** 편집 모드: 클릭한 문장을 선택, Shift+클릭이면 기존 선택과 합쳐 범위로 */
  const onPick = useCallback(
    (segStart: number, segEnd: number, extend: boolean) => {
      const cur = useEditStore.getState().selection;
      const next =
        extend && cur
          ? { start_time: Math.min(cur.start_time, segStart), end_time: Math.max(cur.end_time, segEnd) }
          : { start_time: segStart, end_time: segEnd };
      useEditStore.getState().setSelection(next);
      seek(next.start_time, false);
    },
    [seek],
  );
  const onEdit = useCallback((id: string) => setEditingId(id), []);
  const onDelete = useCallback((id: string) => void deleteSegment(id), [deleteSegment]);
  const onRestore = useCallback((id: string) => void restoreSegment(id), [restoreSegment]);
  const onRevert = useCallback((id: string) => void revertSegment(id), [revertSegment]);

  return (
    <>
      <div className="filters">
        <label className="search">
          <IconSearch />
          <span className="sr-only">대화 내용 검색</span>
          <input type="search" placeholder="대화 내용 검색…" value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
        <label className="select-wrap">
          화자
          <select value={speakerFilter} onChange={(e) => setSpeakerFilter(e.target.value)}>
            <option value="all">전체</option>
            {speakers.map((s) => (
              <option key={s.id} value={s.id}>
                {speakerName(s)}
              </option>
            ))}
          </select>
        </label>
      </div>

      {visible.length === 0 ? (
        <p className="empty">{segments.length ? '조건에 맞는 문장이 없어요.' : '문장이 없어요.'}</p>
      ) : (
        <ol className="seg-list" aria-label="대본">
          {visible.map((s) =>
            s.id === editingId ? (
              <li key={s.id} data-seg-id={s.id}>
                <SegmentEditForm
                  segment={s}
                  speakers={speakers}
                  onSave={(body) => updateSegment(s.id, body)}
                  onCancel={() => setEditingId(null)}
                />
              </li>
            ) : (
              <TranscriptLine
                key={s.id}
                segment={s}
                speaker={speakerById.get(s.speaker_id)}
                active={s.id === activeId}
                cut={cutCoverage(s.start_time, s.end_time, cuts)}
                onPick={editMode ? onPick : undefined}
                selected={!!selection && s.start_time < selection.end_time - 0.01 && s.end_time > selection.start_time + 0.01}
                onSeek={onSeek}
                onEdit={onEdit}
                onDelete={onDelete}
                onRestore={onRestore}
                onRevert={onRevert}
              />
            ),
          )}
        </ol>
      )}
    </>
  );
}
