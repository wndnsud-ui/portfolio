import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import { errorMessage } from '../api/client';
import { episodeApi } from '../api/episodeApi';
import { transcriptApi } from '../api/transcriptApi';
import { AiAssistant } from '../components/ai/AiAssistant';
import { ChapterList } from '../components/ai/ChapterList';
import { AudioPlayer } from '../components/audio/AudioPlayer';
import { AccountMenu } from '../components/common/AccountMenu';
import { Dialog } from '../components/common/Dialog';
import { EditBar } from '../components/audio/EditBar';
import { IconScissors } from '../components/common/Icons';
import { useEditStore } from '../store/editStore';
import { normalize } from '../utils/editOps';
import { IconCheck, IconPencil, IconRedo, IconTrash, IconUpload } from '../components/common/Icons';
import { ExportDialog } from '../components/export/ExportDialog';
import { toastError } from '../components/common/toastStore';
import { EpisodeSidebar } from '../components/episode/EpisodeSidebar';
import { SpeakerManager } from '../components/speaker/SpeakerManager';
import { TranscriptEditor } from '../components/transcript/TranscriptEditor';
import { useEpisodePolling } from '../hooks/useEpisodePolling';
import { useEpisodeStore } from '../store/episodeStore';
import { usePlayerStore } from '../store/playerStore';
import { displayTitle, episodeNumbers, epLabel } from '../utils/episodeStatus';
import { fmtDate, fmtDurationKo } from '../utils/format';
import { findActiveSegment } from '../utils/findActiveSegment';
import { josa } from '../utils/josa';

type Tab = 'transcript' | 'chapters' | 'speakers';

export function EditorPage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const st = useEpisodeStore();
  const { episode, segments, speakers, ai, loadError, save } = st;
  const seek = usePlayerStore((s) => s.seek);
  const playRange = usePlayerStore((s) => s.playRange);
  const [tab, setTab] = useState<Tab>('transcript');
  const [scrollRoot, setScrollRoot] = useState<HTMLElement | null>(null);
  const [reanalyzeOpen, setReanalyzeOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const cutMode = useEditStore((s) => s.active);
  const setCutMode = useEditStore((s) => s.setActive);
  const [skipCuts, setSkipCuts] = useState(true);
  const [exportOpen, setExportOpen] = useState(false);
  const cuts = st.cuts;
  const [editingTitle, setEditingTitle] = useState(false);
  const lastSrcRefresh = useRef(0);

  // 미리 듣기에서 잘린 구간 건너뛰기
  useEffect(() => {
    usePlayerStore.getState().setSkipRanges(skipCuts ? cuts : []);
    return () => usePlayerStore.getState().setSkipRanges([]);
  }, [cuts, skipCuts]);

  useEffect(() => {
    void st.load(id);
    useEditStore.getState().reset();
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  // AI 분석 중이면 상태를 폴링하고, 끝나면 결과를 다시 불러온다
  const aiRunning = episode?.ai_status === 'running';
  useEpisodePolling(aiRunning, async () => {
    const ep = await st.refreshEpisode();
    if (ep && ep.ai_status !== 'running') await st.refreshAi();
  });

  const numbers = useMemo(() => episodeNumbers(st.episodes), [st.episodes]);
  const chapters = ai?.chapters ?? [];
  const segSeq = useMemo(() => new Map(segments.map((s) => [s.id, s.seq])), [segments]);
  const chapterStarts = useMemo(() => chapters.map((c) => c.start_time), [chapters]);
  const activeChapterIdx = usePlayerStore((s) => findActiveSegment(chapterStarts, s.currentTime));

  const onSourceError = useCallback(() => {
    // Signed URL 만료 → 재발급 (1분에 한 번까지)
    if (Date.now() - lastSrcRefresh.current < 60_000) return;
    lastSrcRefresh.current = Date.now();
    void st.refreshEpisode();
  }, [st]);

  if (episode && episode.id === id && episode.status !== 'transcribed') {
    return <Navigate to={`/episodes/${id}/processing`} replace />;
  }

  const editedCount = segments.filter((s) => s.edited_text !== null).length;
  const namedCount = speakers.filter((s) => s.display_name).length;
  const n = numbers.get(id);

  return (
    <div className="app-shell">
      <div className="app-body">
        <EpisodeSidebar activeId={id} showRecent />
        <main className="app-main" ref={setScrollRoot} tabIndex={-1}>
          {loadError ? (
            <div className="empty">
              <p>{loadError}</p>
              <p style={{ marginTop: 12 }}>
                <Link to="/" className="btn">
                  프로젝트로
                </Link>
              </p>
            </div>
          ) : !episode || episode.id !== id ? (
            <p className="empty">불러오는 중…</p>
          ) : (
            <div className="editor-main">
              <header className="editor-head">
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 0, flex: '1 1 320px' }}>
                  {editingTitle ? (
                    <form
                      style={{ display: 'flex', gap: 8, alignItems: 'center' }}
                      onSubmit={(e) => {
                        e.preventDefault();
                        const v = new FormData(e.currentTarget).get('title') as string;
                        void st.renameEpisode(v);
                        setEditingTitle(false);
                      }}
                    >
                      <label style={{ flex: 1 }}>
                        <span className="sr-only">에피소드 제목</span>
                        <input
                          name="title"
                          className="text-input"
                          style={{ width: '100%', height: 40, fontSize: 18, fontWeight: 600 }}
                          defaultValue={episode.title ?? ''}
                          placeholder={displayTitle(episode)}
                          maxLength={200}
                          autoFocus
                          onKeyDown={(e) => e.key === 'Escape' && setEditingTitle(false)}
                        />
                      </label>
                      <button type="submit" className="btn btn-primary btn-sm">
                        저장
                      </button>
                      <button type="button" className="btn btn-sm" onClick={() => setEditingTitle(false)}>
                        취소
                      </button>
                    </form>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <h1 className="editor-title">
                        {n ? `${epLabel(n)} ` : ''}
                        {displayTitle(episode)}
                      </h1>
                      <button type="button" className="icon-btn icon-btn-sm" aria-label="제목 수정" onClick={() => setEditingTitle(true)}>
                        <IconPencil />
                      </button>
                    </div>
                  )}
                  <div className="editor-meta">
                    <span>{fmtDate(episode.created_at, '. ')}</span>
                    <span>{fmtDurationKo(episode.duration)}</span>
                    <span>{speakers.length}명의 화자</span>
                    {editedCount > 0 && <span>직접 고친 문장 {editedCount}개</span>}
                    {episode.stt_model === 'mock' && (
                      <span className="pill pill-warn" title="OPENAI_API_KEY를 넣고 '음성 다시 분석'을 누르면 실제 결과로 바뀌어요">
                        모의 결과
                      </span>
                    )}
                    {save === 'saving' && <span>저장 중…</span>}
                    {(save === 'saved' || save === 'idle') && (
                      <span className="save-ok">
                        <IconCheck size={14} strokeWidth={2.2} />
                        자동 저장됨
                      </span>
                    )}
                    {save === 'error' && <span className="save-err">저장하지 못한 변경이 있어요</span>}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <button
                    type="button"
                    className="btn"
                    style={{ height: 40, width: 40, padding: 0 }}
                    aria-label="에피소드 삭제"
                    title="에피소드 삭제"
                    onClick={() => setDeleteOpen(true)}
                    disabled={aiRunning}
                  >
                    <IconTrash />
                  </button>
                  <button type="button" className="btn" style={{ height: 40 }} onClick={() => setReanalyzeOpen(true)} disabled={aiRunning}>
                    <IconRedo />
                    음성 다시 분석
                  </button>
                  <button
                    type="button"
                    className={`btn${cutMode ? ' btn-soft' : ''}`}
                    style={{ height: 40 }}
                    aria-pressed={cutMode}
                    onClick={() => setCutMode(!cutMode)}
                  >
                    <IconScissors />
                    편집{cuts.length > 0 && ` · 잘림 ${cuts.length}`}
                  </button>
                  <button type="button" className="btn btn-primary" style={{ height: 40 }} onClick={() => setExportOpen(true)}>
                    <IconUpload size={16} />
                    내보내기
                  </button>
                  <AccountMenu size={40} />
                </div>
              </header>

              <div className="editor-cols">
                <section aria-label="트랜스크립트" className="card transcript-panel">
                  <div role="tablist" aria-label="편집 보기" className="tabs">
                    {(
                      [
                        ['transcript', '트랜스크립트'],
                        ['chapters', '챕터'],
                        ['speakers', '화자'],
                      ] as [Tab, string][]
                    ).map(([k, label]) => (
                      <button key={k} type="button" role="tab" className="tab" aria-selected={tab === k} onClick={() => setTab(k)}>
                        {label}
                      </button>
                    ))}
                  </div>
                  <div role="tabpanel">
                    {tab === 'transcript' && <TranscriptEditor scrollRoot={scrollRoot} />}
                    {tab === 'chapters' && (
                      <ChapterList
                        chapters={chapters}
                        onSeek={(t) => seek(t)}
                        variant="full"
                        segSeq={segSeq}
                        activeId={activeChapterIdx >= 0 ? chapters[activeChapterIdx]?.id : null}
                      />
                    )}
                    {tab === 'speakers' && (
                      <div style={{ padding: 16 }}>
                        <SpeakerManager compact onPlaySample={playRange} />
                        <p style={{ marginTop: 12 }}>
                          <Link to={`/episodes/${id}/speakers`} className="small">
                            화자 관리 화면에서 크게 보기
                          </Link>
                        </p>
                      </div>
                    )}
                  </div>
                </section>
                <AiAssistant />
              </div>
            </div>
          )}
        </main>
      </div>

      {episode && episode.id === id && cutMode && (
        <EditBar duration={episode.duration ?? 0} skip={skipCuts} onSkipChange={setSkipCuts} />
      )}

      {episode && episode.id === id && (
        <AudioPlayer
          key={episode.id}
          src={episode.playback_url}
          peaksUrl={episode.peaks_url}
          duration={episode.duration ?? 0}
          chapters={chapters}
          cuts={cuts}
          onCutsChange={(c) => useEditStore.getState().apply(normalize(c, episode.duration ?? 0))}
          onSourceError={onSourceError}
        />
      )}

      {exportOpen && episode && <ExportDialog episodeId={id} cuts={cuts} onClose={() => setExportOpen(false)} />}

      {deleteOpen && episode && (
        <Dialog
          title="에피소드를 삭제할까요?"
          description={`“${displayTitle(episode)}”의 음성 파일, 대본, AI 결과가 모두 지워지고 되돌릴 수 없어요.`}
          onClose={() => setDeleteOpen(false)}
          actions={
            <>
              <button type="button" className="btn" onClick={() => setDeleteOpen(false)}>
                취소
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={async () => {
                  try {
                    usePlayerStore.getState().audio?.pause();
                    await episodeApi.remove(id);
                    await st.loadList();
                    navigate('/', { replace: true });
                  } catch (e) {
                    toastError(errorMessage(e, '삭제하지 못했어요.'));
                  }
                }}
              >
                삭제
              </button>
            </>
          }
        />
      )}

      {reanalyzeOpen && episode && (
        <Dialog
          title="음성을 처음부터 다시 분석할까요?"
          onClose={() => setReanalyzeOpen(false)}
          actions={
            <>
              <button type="button" className="btn" onClick={() => setReanalyzeOpen(false)}>
                취소
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={async () => {
                  try {
                    await transcriptApi.reanalyze(id);
                    setReanalyzeOpen(false);
                    navigate(`/episodes/${id}/processing`);
                  } catch (e) {
                    toastError(errorMessage(e, '다시 분석을 시작하지 못했어요.'));
                  }
                }}
              >
                다시 분석
              </button>
            </>
          }
        >
          <ul className="warn-list">
            {editedCount > 0 && <li>직접 고친 문장 {editedCount}개가 STT 원문으로 돌아가요</li>}
            {(namedCount > 0 || st.mergeCount > 0) && (
              <li>
                {josa(
                  [namedCount > 0 && `화자 이름 ${namedCount}개`, st.mergeCount > 0 && `병합 ${st.mergeCount}건`].filter(Boolean).join('와 '),
                  '이/가',
                )}{' '}
                초기화돼요
              </li>
            )}
            {segments.some((s) => s.is_deleted) && <li>삭제한 문장이 다시 나타나요</li>}
            <li>요약 · 챕터 · 하이라이트도 새로 만들어요</li>
          </ul>
          <p className="small muted">문장 몇 개만 틀렸다면 다시 분석하지 말고 해당 문장을 직접 고치는 편이 빨라요.</p>
        </Dialog>
      )}
    </div>
  );
}
