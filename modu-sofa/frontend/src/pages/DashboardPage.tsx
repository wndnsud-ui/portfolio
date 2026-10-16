import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { errorMessage } from '../api/client';
import { episodeApi } from '../api/episodeApi';
import { AccountMenu } from '../components/common/AccountMenu';
import { Dialog } from '../components/common/Dialog';
import { IconPlus } from '../components/common/Icons';
import { toastError } from '../components/common/toastStore';
import { EpisodeCard } from '../components/episode/EpisodeCard';
import { EpisodeSidebar } from '../components/episode/EpisodeSidebar';
import { FileDropzone } from '../components/upload/FileDropzone';
import { useEpisodePolling } from '../hooks/useEpisodePolling';
import { useEpisodeStore } from '../store/episodeStore';
import type { Episode } from '../types/episode';
import { cardKind, displayTitle, episodeNumbers } from '../utils/episodeStatus';

export function DashboardPage() {
  const episodes = useEpisodeStore((s) => s.episodes);
  const listLoaded = useEpisodeStore((s) => s.listLoaded);
  const loadList = useEpisodeStore((s) => s.loadList);
  const setPendingFiles = useEpisodeStore((s) => s.setPendingFiles);
  const navigate = useNavigate();
  const [deleting, setDeleting] = useState<Episode | null>(null);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  const busy = episodes.some((e) => ['progress', 'aiRunning'].includes(cardKind(e)));
  useEpisodePolling(busy, loadList, 5000);

  const numbers = useMemo(() => episodeNumbers(episodes), [episodes]);

  return (
    <div className="app-shell">
      <div className="app-body">
        <EpisodeSidebar />
        <main className="app-main">
          <div className="dash">
            <header className="page-head">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <h1>프로젝트</h1>
                <p className="muted">에피소드 {episodes.length}개</p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <Link to="/upload" className="btn btn-primary">
                  <IconPlus />새 에피소드
                </Link>
                <AccountMenu />
              </div>
            </header>

            <FileDropzone
              variant="wide"
              onFiles={(files) => {
                setPendingFiles(files);
                navigate('/upload');
              }}
            />

            {listLoaded && episodes.length === 0 ? (
              <p className="empty">아직 에피소드가 없어요. 음성 파일을 올려 첫 에피소드를 만들어 보세요.</p>
            ) : (
              <section aria-label="에피소드 목록" className="ep-grid">
                {episodes.map((ep) => (
                  <EpisodeCard key={ep.id} episode={ep} number={numbers.get(ep.id)} onDelete={setDeleting} />
                ))}
              </section>
            )}
          </div>
        </main>
      </div>

      {deleting && (
        <Dialog
          title="에피소드를 삭제할까요?"
          description={`“${displayTitle(deleting)}”의 음성 파일, 대본, AI 결과가 모두 지워지고 되돌릴 수 없어요.`}
          onClose={() => setDeleting(null)}
          actions={
            <>
              <button type="button" className="btn" onClick={() => setDeleting(null)}>
                취소
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={async () => {
                  try {
                    await episodeApi.remove(deleting.id);
                    setDeleting(null);
                    await loadList();
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
    </div>
  );
}
