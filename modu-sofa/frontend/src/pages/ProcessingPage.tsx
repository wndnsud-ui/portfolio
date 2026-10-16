import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { errorMessage } from '../api/client';
import { episodeApi } from '../api/episodeApi';
import { transcriptApi } from '../api/transcriptApi';
import { Brand } from '../components/common/Brand';
import { IconBack, IconMusic } from '../components/common/Icons';
import { toastError } from '../components/common/toastStore';
import { ProcessingSteps } from '../components/status/ProcessingSteps';
import { useEpisodePolling } from '../hooks/useEpisodePolling';
import type { EpisodeDetail } from '../types/episode';
import { Dialog } from '../components/common/Dialog';
import { CANCELLED_MSG, SERVER_RESTART_MSG } from '../utils/episodeStatus';
import { fmtMB, fmtTime } from '../utils/format';

export function ProcessingPage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const [ep, setEp] = useState<EpisodeDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  const load = useCallback(async () => {
    try {
      setEp(await episodeApi.get(id));
    } catch (e) {
      setLoadError(errorMessage(e, '에피소드를 불러오지 못했어요.'));
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  const failed = ep?.status === 'failed';
  const done = ep?.status === 'transcribed' && ep.ai_status !== 'running';
  useEpisodePolling(!!ep && !failed && !done, load, 3000);

  // 모두 끝나면 에디터로 이동
  useEffect(() => {
    if (ep?.status === 'transcribed' && ep.ai_status === 'completed') {
      const t = window.setTimeout(() => navigate(`/episodes/${id}`, { replace: true }), 900);
      return () => window.clearTimeout(t);
    }
  }, [ep?.status, ep?.ai_status, id, navigate]);

  if (loadError) {
    return (
      <div className="center-page">
        <p className="empty">{loadError}</p>
        <Link to="/" className="btn">
          프로젝트로
        </Link>
      </div>
    );
  }

  const interrupted = ep?.error_message === SERVER_RESTART_MSG;
  const cancelled = ep?.error_message === CANCELLED_MSG;
  const running = !!ep && (['uploaded', 'processing', 'transcribing'].includes(ep.status) || ep.ai_status === 'running');
  const hasOldTranscript = (ep?.counts?.speakers ?? 0) > 0;
  const uploadFailed = failed && ep?.error_stage === 'upload';
  const aiFailed = ep?.status === 'transcribed' && ep.ai_status === 'failed';
  const transcriptReady = ep?.status === 'transcribed';

  const retry = async () => {
    setRetrying(true);
    try {
      await transcriptApi.reanalyze(id);
      await load();
    } catch (e) {
      toastError(errorMessage(e, '다시 분석을 시작하지 못했어요.'));
    } finally {
      setRetrying(false);
    }
  };

  const cancel = async () => {
    setCancelling(true);
    try {
      const r = await transcriptApi.cancel(id);
      setCancelOpen(false);
      // 재분석을 취소해 기존 대본으로 돌아갔으면 에디터로
      if (r.status === 'transcribed') navigate(`/episodes/${id}`, { replace: true });
      else await load();
    } catch (e) {
      toastError(errorMessage(e, '취소하지 못했어요.'));
      await load();
    } finally {
      setCancelling(false);
    }
  };

  return (
    <div className="center-page">
      <div className="center-top" style={{ maxWidth: 640 }}>
        <Link to="/" className="back-link">
          <IconBack />
          프로젝트로
        </Link>
        <Brand size={14} mark />
      </div>

      <section aria-label="분석 진행 상태" className="panel-card" style={{ width: '100%', maxWidth: 640, display: 'flex', flexDirection: 'column', gap: 24 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, letterSpacing: '-0.01em' }}>
            {cancelled ? '분석을 취소했어요' : failed ? '분석이 멈췄어요' : transcriptReady ? (aiFailed ? 'Transcript가 준비됐어요' : '거의 다 됐어요') : 'AI가 음성을 분석하고 있어요'}
          </h1>
          <p className="muted">
            {failed
              ? uploadFailed
                ? '파일을 다시 올려 주세요.'
                : '파일은 안전하게 보관되어 있어요.'
              : transcriptReady
                ? '에디터에서 바로 대본을 확인하고 재생할 수 있어요.'
                : '끝나면 에디터에서 바로 확인할 수 있어요.'}
          </p>
        </div>

        {ep && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '14px 16px', borderRadius: 12, background: '#F7F6FB' }}>
            <span className="file-icon" aria-hidden="true">
              <IconMusic stroke="#4A2FD0" />
            </span>
            <span style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {ep.original_filename ?? ep.title ?? '음성 파일'}
              </span>
              <span className="mono xsmall muted">
                {ep.duration ? `${fmtTime(ep.duration)} · ` : ''}
                {fmtMB(ep.file_size).replace('MB', ' MB')}
              </span>
            </span>
            {ep.stt_model && (
              <span className={`pill ${ep.stt_model === 'mock' ? 'pill-warn' : 'pill-primary'}`} title={ep.stt_model}>
                {ep.stt_model === 'mock' ? '모의 분석' : 'OpenAI 분석'}
              </span>
            )}
          </div>
        )}

        {ep ? <ProcessingSteps episode={ep} /> : <p className="muted">불러오는 중…</p>}

        {failed && (
          <div role="alert" className="alert alert-danger" style={{ flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 14, padding: 16 }}>
            <span style={{ flex: '1 1 260px', display: 'flex', flexDirection: 'column', gap: 2 }}>
              <span className="alert-title">
                {cancelled ? '분석을 취소했어요.' : interrupted ? '서버 점검으로 분석이 중단됐어요.' : uploadFailed ? '파일을 확인하지 못했어요.' : '음성 분석 중 오류가 발생했습니다.'}
              </span>
              <span className="alert-body">
                {cancelled
                  ? '업로드한 파일은 그대로 있으니 언제든 다시 분석할 수 있어요.'
                  : interrupted
                  ? '분석 도중 서버가 다시 시작됐어요. 파일은 그대로 있으니 다시 분석하면 처음부터 다시 진행해요.'
                  : ep?.error_message ?? '업로드한 파일은 그대로 있으니 다시 시도할 수 있어요.'}
              </span>
            </span>
            {uploadFailed ? (
              <Link to="/upload" className="btn btn-primary">
                다른 파일 올리기
              </Link>
            ) : (
              <button type="button" className="btn btn-primary" onClick={() => void retry()} disabled={retrying}>
                다시 분석하기
              </button>
            )}
          </div>
        )}

        {transcriptReady && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="small muted">
              {aiFailed ? 'AI 분석만 실패했어요. 에디터에서 다시 실행할 수 있어요.' : 'AI 분석이 끝나면 자동으로 에디터로 이동해요.'}
            </span>
            <Link to={`/episodes/${id}`} className="btn btn-primary">
              에디터 열기
            </Link>
          </div>
        )}

        {running && (
          <div
            style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 12, borderTop: '1px solid var(--line-soft)', paddingTop: 16 }}
          >
            <p className="small muted" style={{ flex: '1 1 280px' }}>
              {transcriptReady
                ? 'AI 분석을 취소해도 대본은 그대로 남아요.'
                : '창을 닫아도 분석은 계속돼요. 끝나면 프로젝트 목록에서 바로 열 수 있어요.'}
            </p>
            <button type="button" className="btn btn-sm" onClick={() => setCancelOpen(true)}>
              분석 취소
            </button>
          </div>
        )}
      </section>

      {cancelOpen && ep && (
        <Dialog
          title={transcriptReady ? 'AI 분석을 취소할까요?' : '음성 분석을 취소할까요?'}
          onClose={() => setCancelOpen(false)}
          actions={
            <>
              <button type="button" className="btn" onClick={() => setCancelOpen(false)}>
                계속 분석
              </button>
              <button type="button" className="btn btn-danger" onClick={() => void cancel()} disabled={cancelling}>
                분석 취소
              </button>
            </>
          }
        >
          <ul className="warn-list">
            <li>지금까지 진행한 분석 결과는 저장되지 않아요</li>
            {!transcriptReady && (
              <li>{hasOldTranscript ? '기존 대본과 고친 내용은 그대로 남아요' : '업로드한 파일은 남아 있어서 나중에 다시 분석할 수 있어요'}</li>
            )}
            {ep.stt_model !== 'mock' && <li>이미 OpenAI에 보낸 구간은 요금이 청구될 수 있어요</li>}
          </ul>
        </Dialog>
      )}
    </div>
  );
}
