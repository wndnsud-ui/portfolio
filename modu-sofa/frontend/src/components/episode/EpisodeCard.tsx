import { Link } from 'react-router-dom';
import type { Episode } from '../../types/episode';
import { CANCELLED_MSG, cardKind, displayTitle, episodeHref, epLabel, progressLabel, SERVER_RESTART_MSG } from '../../utils/episodeStatus';
import { fmtDate, fmtRelative, fmtTime } from '../../utils/format';
import { IconTrash } from '../common/Icons';

interface Props {
  episode: Episode;
  number?: number;
  onDelete: (ep: Episode) => void;
}

export function EpisodeCard({ episode: ep, number, onDelete }: Props) {
  const kind = cardKind(ep);
  const title = displayTitle(ep);
  const when = kind === 'done' || kind === 'aiFailed' || kind === 'aiRunning' ? fmtDate(ep.created_at) : fmtRelative(ep.created_at);
  const c = ep.counts;
  const canDelete = kind !== 'progress' && kind !== 'aiRunning';

  return (
    <div className="ep-card-wrap">
      <Link to={episodeHref(ep)} className={`ep-card${kind === 'failed' ? ' failed' : ''}`}>
        <span className="ep-card-top">
          <span className="mono small muted">{epLabel(number)}</span>
          {kind === 'progress' && (
            <span className="pill pill-primary">
              <span className="pill-dot" />
              {progressLabel(ep).label}
            </span>
          )}
          {kind === 'failed' && ep.error_message === CANCELLED_MSG && <span className="pill pill-muted">분석 취소됨</span>}
          {kind === 'failed' && ep.error_message !== CANCELLED_MSG && (
            <span className="pill pill-danger">{ep.error_stage === 'upload' ? '업로드 실패' : '분석 실패'}</span>
          )}
          {kind === 'aiFailed' && <span className="pill pill-warn">AI 분석 실패</span>}
          {kind === 'aiRunning' && (
            <span className="pill pill-primary">
              <span className="pill-dot" />
              AI 분석 중
            </span>
          )}
          {kind === 'done' && <span className="pill pill-ok">완료</span>}
          {kind === 'draft' && <span className="pill pill-muted">업로드 전</span>}
        </span>

        <span className="ep-card-title">{title}</span>

        {kind === 'progress' && (
          <span className="progress thin">
            <span style={{ width: `${progressLabel(ep).pct}%` }} />
          </span>
        )}
        {kind === 'failed' && (
          <span className="small" style={{ color: '#A61B1B' }}>
            {ep.error_message === CANCELLED_MSG
              ? '분석을 취소했어요 · 다시 분석하기'
              : ep.error_message === SERVER_RESTART_MSG
              ? '서버 점검으로 분석이 중단됐어요 · 다시 분석하기'
              : ep.error_stage === 'upload'
                ? `${ep.error_message ?? '업로드에 실패했어요.'}`
                : '음성 분석 중 오류가 발생했습니다 · 다시 분석하기'}
          </span>
        )}
        {kind === 'aiFailed' && <span className="small" style={{ color: 'var(--ink-3)' }}>Transcript 사용 가능 · AI 분석만 다시 실행</span>}
        {(kind === 'done' || kind === 'aiRunning') && c && (
          <span className="small" style={{ color: 'var(--ink-3)' }}>
            화자 {c.speakers}명 · 챕터 {c.chapters}개 · 하이라이트 {c.highlights}개
          </span>
        )}

        <span className="small muted">
          {ep.duration ? `${fmtTime(ep.duration)} · ` : ''}
          {when}
        </span>
      </Link>
      {canDelete && (
        <button type="button" className="ep-card-del" aria-label={`${title} 삭제`} onClick={() => onDelete(ep)}>
          <IconTrash />
        </button>
      )}
    </div>
  );
}
