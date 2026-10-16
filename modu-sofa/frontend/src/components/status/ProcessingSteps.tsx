import type { EpisodeDetail } from '../../types/episode';
import { fmtTime } from '../../utils/format';
import { IconAlert, IconCheck } from '../common/Icons';

type Kind = 'done' | 'active' | 'error' | 'todo';

interface StepDef {
  label: string;
  detail: string;
  kind: Kind;
  progress?: { pct: number; text: string } | null;
}

/** episode 상태 → 5단계 (업로드 → 오디오 준비 → 음성 분석(구간 n/N) → Transcript 생성 → AI 분석) */
export function buildSteps(ep: EpisodeDetail): StepDef[] {
  const s = ep.status;
  const total = Math.max(1, ep.progress_total);
  const sttDone = s === 'transcribed' || (s === 'transcribing' && ep.progress_current >= ep.progress_total && ep.progress_total > 0);

  // 진행 위치(0~4)
  let at = 0;
  if (s === 'created' || s === 'uploading') at = 0;
  else if (s === 'uploaded' || s === 'processing') at = 1;
  else if (s === 'transcribing') at = sttDone ? 3 : 2;
  else if (s === 'transcribed') at = ep.ai_status === 'completed' ? 5 : 4;
  else if (s === 'failed') {
    at =
      ep.error_stage === 'upload'
        ? 0
        : ep.error_stage === 'processing'
          ? 1
          : ep.progress_total > 0 && ep.progress_current >= ep.progress_total
            ? 3
            : 2;
  }
  const failedStep = s === 'failed' ? at : s === 'transcribed' && ep.ai_status === 'failed' ? 4 : -1;
  const kindAt = (i: number): Kind => (i === failedStep ? 'error' : i < at ? 'done' : i === at ? 'active' : 'todo');

  const n = Math.min(total, ep.progress_current + 1);
  const step = ep.stt_chunk_sec - ep.stt_overlap_sec;
  const chunkStart = (n - 1) * step;
  const chunkEnd = Math.min(chunkStart + ep.stt_chunk_sec, ep.duration ?? chunkStart + ep.stt_chunk_sec);

  return [
    { label: '파일 업로드', detail: kindAt(0) === 'done' ? 'Storage에 저장 완료' : '파일을 올리고 있어요', kind: kindAt(0) },
    {
      label: '오디오 준비',
      detail: kindAt(1) === 'done' ? '재생용 파일과 파형 데이터를 만들었어요' : '재생용 파일과 파형 데이터를 만들고 구간을 나눠요',
      kind: kindAt(1),
    },
    {
      label: '음성 분석',
      detail: '화자를 구분하며 문장 단위로 받아 적는 중',
      kind: kindAt(2),
      progress:
        kindAt(2) === 'active' && ep.progress_total > 0
          ? {
              pct: Math.max(4, Math.round((ep.progress_current / total) * 100)),
              text: `구간 ${n} / ${total} · ${fmtTime(chunkStart)} ~ ${fmtTime(chunkEnd)}`,
            }
          : null,
    },
    { label: 'Transcript 생성', detail: '구간을 이어 붙이고 화자를 하나로 맞춰요', kind: kindAt(3) },
    { label: 'AI 분석', detail: '요약 · 제목 추천 · 챕터 · 하이라이트', kind: kindAt(4) },
  ];
}

const STATE_TEXT: Record<Kind, string> = { done: '완료', active: '진행 중', error: '실패', todo: '대기' };

export function ProcessingSteps({ episode }: { episode: EpisodeDetail }) {
  const steps = buildSteps(episode);
  const cancelled = episode.error_message === '분석을 취소했어요.';
  return (
    <ol className="steps" aria-label="분석 단계">
      {steps.map((st, i) => (
        <li key={st.label}>
          <span className="step-rail">
            <span className={`step-dot ${st.kind}`}>
              {st.kind === 'done' && <IconCheck size={14} stroke="#FFFFFF" strokeWidth={3} />}
              {st.kind === 'error' && <IconAlert stroke="#FFFFFF" />}
              {st.kind === 'active' && <span className="pulse" />}
            </span>
            {i < steps.length - 1 && <span className={`step-line${st.kind === 'done' ? ' done' : ''}`} />}
          </span>
          <span className="step-body">
            <span className={`step-label ${st.kind}`}>
              {st.label} <span style={{ fontWeight: 400, color: 'var(--muted)', fontSize: 13 }}>{cancelled && st.kind === 'error' ? '취소' : STATE_TEXT[st.kind]}</span>
            </span>
            <span className="small muted">{st.detail}</span>
            {st.progress && (
              <span style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 6 }}>
                <span className="progress">
                  <span style={{ width: `${st.progress.pct}%` }} />
                </span>
                <span className="mono xsmall" style={{ color: 'var(--ink-3)' }}>
                  {st.progress.text}
                </span>
              </span>
            )}
          </span>
        </li>
      ))}
    </ol>
  );
}
