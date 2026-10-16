import type { Episode } from '../types/episode';

export type CardKind = 'progress' | 'failed' | 'aiFailed' | 'aiRunning' | 'done' | 'draft';

export function cardKind(ep: Episode): CardKind {
  if (ep.status === 'failed') return 'failed';
  if (ep.status === 'created') return 'draft';
  if (ep.status !== 'transcribed') return 'progress';
  if (ep.ai_status === 'failed') return 'aiFailed';
  if (ep.ai_status === 'running' || ep.ai_status === 'none') return 'aiRunning';
  return 'done';
}

export function progressLabel(ep: Episode): { label: string; pct: number } {
  switch (ep.status) {
    case 'uploading':
      return { label: '업로드 중', pct: 5 };
    case 'uploaded':
    case 'processing':
      return { label: '오디오 준비 중', pct: 12 };
    case 'transcribing': {
      const total = Math.max(1, ep.progress_total);
      if (ep.progress_current >= total) return { label: 'Transcript 생성 중', pct: 92 };
      const n = Math.min(total, ep.progress_current + 1);
      return { label: `음성 분석 중 · ${n}/${total}`, pct: 15 + Math.round((ep.progress_current / total) * 75) };
    }
    default:
      return { label: '분석 중', pct: 10 };
  }
}

/** 처리 화면으로 가야 하는지(아직 에디터를 열 수 없는 상태) */
export function needsProcessingView(ep: Episode): boolean {
  return ep.status !== 'transcribed';
}

export function episodeHref(ep: Episode): string {
  return needsProcessingView(ep) ? `/episodes/${ep.id}/processing` : `/episodes/${ep.id}`;
}

export const SERVER_RESTART_MSG = '서버 재시작으로 작업이 중단되었습니다';
export const CANCELLED_MSG = '분석을 취소했어요.';

/** 생성 순서 기준 에피소드 번호 (EP.01부터) */
export function episodeNumbers(episodes: Episode[]): Map<string, number> {
  const sorted = [...episodes].sort((a, b) => a.created_at.localeCompare(b.created_at));
  const map = new Map<string, number>();
  let n = 0;
  for (const e of sorted) {
    if (e.status === 'transcribed') map.set(e.id, ++n);
  }
  return map;
}

export const epLabel = (n: number | undefined) => (n ? `EP.${String(n).padStart(2, '0')}` : '초안');

export const displayTitle = (ep: Pick<Episode, 'title' | 'original_filename'>) =>
  ep.title || ep.original_filename?.replace(/\.(mp3|wav|m4a)$/i, '') || '제목 미정';
