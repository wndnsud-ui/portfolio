import { useEffect, useState } from 'react';
import { useEpisodeStore } from '../../store/episodeStore';
import { speakerName, type Speaker } from '../../types/speaker';
import { fmtTime } from '../../utils/format';
import { IconPlayFill } from '../common/Icons';
import { SpeakerAvatar } from '../transcript/SpeakerBadge';
import { SpeakerMergeDialog } from './SpeakerMergeDialog';

interface Props {
  /** 대표 구간 듣기 (에디터에서는 공용 플레이어, 화자 화면에서는 그 화면의 플레이어) */
  onPlaySample: (start: number, end: number) => void;
  compact?: boolean;
}

function NameInput({ speaker, onSave }: { speaker: Speaker; onSave: (name: string) => void }) {
  const [value, setValue] = useState(speaker.display_name ?? '');
  useEffect(() => setValue(speaker.display_name ?? ''), [speaker.display_name]);
  const commit = () => {
    if (value.trim() !== (speaker.display_name ?? '')) onSave(value);
  };
  return (
    <input
      type="text"
      className="spk-input"
      value={value}
      placeholder="이름 입력"
      maxLength={40}
      onChange={(e) => setValue(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
        if (e.key === 'Escape') setValue(speaker.display_name ?? '');
      }}
    />
  );
}

export function SpeakerManager({ onPlaySample, compact = false }: Props) {
  const speakers = useEpisodeStore((s) => s.speakers);
  const lastMerge = useEpisodeStore((s) => s.lastMerge);
  const renameSpeaker = useEpisodeStore((s) => s.renameSpeaker);
  const mergeSpeakers = useEpisodeStore((s) => s.mergeSpeakers);
  const undoMerge = useEpisodeStore((s) => s.undoMerge);
  const [mergeFrom, setMergeFrom] = useState<Speaker | null>(null);
  const [bannerHidden, setBannerHidden] = useState(false);

  const into = lastMerge ? speakers.find((s) => s.id === lastMerge.into_speaker_id) : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: compact ? 12 : 18 }}>
      <p className={compact ? 'small muted' : 'muted'}>
        이름을 바꾸면 이 에피소드의 모든 문장에 한 번에 반영돼요.
        {compact
          ? ' 한 사람이 둘로 나뉘었다면 병합하세요.'
          : ' 긴 녹음은 자동 분석에서 같은 사람이 둘로 나뉠 수 있어요. 대표 구간을 들어보고 병합하세요.'}
      </p>

      {lastMerge && !bannerHidden && (
        <div
          role="status"
          className="alert-ok"
          style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 10, padding: '12px 16px', borderRadius: 12 }}
        >
          <span>
            {lastMerge.from_display_name ?? lastMerge.from_speaker_code}의 문장 {lastMerge.segment_count}개를{' '}
            {into ? speakerName(into) : '다른 화자'}에 합쳤어요.
          </span>
          <span style={{ display: 'flex', gap: 6 }}>
            <button
              type="button"
              className="btn btn-sm"
              style={{ borderColor: 'var(--ok-line)', color: 'var(--ok-ink)', fontWeight: 600 }}
              onClick={() => void undoMerge()}
            >
              되돌리기
            </button>
            <button type="button" className="icon-btn icon-btn-sm" aria-label="안내 닫기" onClick={() => setBannerHidden(true)}>
              ✕
            </button>
          </span>
        </div>
      )}

      <ul style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {speakers.map((p) => (
          <li key={p.id} className={`spk-row${p.suspect ? ' suspect' : ''}`}>
            <SpeakerAvatar speaker={p} size={compact ? 36 : 40} />
            <label style={{ flex: '1 1 220px', display: 'flex', flexDirection: 'column', gap: 3, fontSize: 12, color: 'var(--muted)' }}>
              <span>
                <span className="mono">{p.speaker_code}</span> · 문장 {p.segment_count}개 · {Math.round(p.share * 100)}%
                {p.suspect && <span style={{ color: '#8A4B05', fontWeight: 600 }}> · 확인 필요</span>}
              </span>
              <NameInput speaker={p} onSave={(name) => void renameSpeaker(p.id, name)} />
            </label>
            <button
              type="button"
              className="btn btn-sm"
              style={{ height: 38 }}
              disabled={p.sample_start == null}
              aria-label={`${p.speaker_code} 대표 구간 듣기`}
              title={p.sample_start != null ? `${fmtTime(p.sample_start)} ~ ${fmtTime(p.sample_end)}` : undefined}
              onClick={() => p.sample_start != null && onPlaySample(p.sample_start, p.sample_end ?? p.sample_start + 10)}
            >
              <IconPlayFill />
              대표 구간
            </button>
            <button
              type="button"
              className="btn btn-sm"
              style={{ height: 38 }}
              disabled={speakers.length < 2}
              onClick={() => setMergeFrom(p)}
            >
              {compact ? '다른 화자로 병합' : '병합'}
            </button>
          </li>
        ))}
      </ul>

      {mergeFrom && (
        <SpeakerMergeDialog
          from={mergeFrom}
          speakers={speakers}
          onClose={() => setMergeFrom(null)}
          onConfirm={async (intoId) => {
            const ok = await mergeSpeakers(mergeFrom.id, intoId);
            if (ok) {
              setBannerHidden(false);
              setMergeFrom(null);
            }
          }}
        />
      )}
    </div>
  );
}
