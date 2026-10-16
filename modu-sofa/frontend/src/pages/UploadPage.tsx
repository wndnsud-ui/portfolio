import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { errorMessage } from '../api/client';
import { episodeApi } from '../api/episodeApi';
import { uploadApi, type UploadHandle } from '../api/uploadApi';
import { Brand } from '../components/common/Brand';
import { IconBack } from '../components/common/Icons';
import { FileDropzone } from '../components/upload/FileDropzone';
import { RejectedFiles, SelectedFile } from '../components/upload/FileValidationList';
import { useEpisodeStore } from '../store/episodeStore';
import { checkFile, type CheckedFile } from '../utils/fileValidation';

type Phase = 'empty' | 'checking' | 'ready' | 'uploading' | 'verifying';

export function UploadPage() {
  const navigate = useNavigate();
  const pendingFiles = useEpisodeStore((s) => s.pendingFiles);
  const setPendingFiles = useEpisodeStore((s) => s.setPendingFiles);

  const [title, setTitle] = useState('');
  const [phase, setPhase] = useState<Phase>('empty');
  const [selected, setSelected] = useState<CheckedFile | null>(null);
  const [rejected, setRejected] = useState<CheckedFile[]>([]);
  const [progress, setProgress] = useState<{ loaded: number; total: number } | null>(null);
  const handle = useRef<UploadHandle | null>(null);
  const episodeId = useRef<string | null>(null);

  const pick = async (files: File[]) => {
    setPhase('checking');
    setRejected([]);
    const checked = await Promise.all(files.map(checkFile));
    const ok = checked.find((c) => !c.error) ?? null;
    setRejected(checked.filter((c) => c.error));
    setSelected(ok);
    setPhase(ok ? 'ready' : 'empty');
  };

  useEffect(() => {
    if (pendingFiles.length) {
      void pick(pendingFiles);
      setPendingFiles([]);
    }
  }, [pendingFiles]); // eslint-disable-line react-hooks/exhaustive-deps

  const cleanupEpisode = async () => {
    const id = episodeId.current;
    episodeId.current = null;
    if (id) await episodeApi.remove(id).catch(() => undefined);
  };

  const start = async () => {
    if (!selected) return;
    setPhase('uploading');
    setProgress({ loaded: 0, total: selected.file.size });
    try {
      const ep = await episodeApi.create(title.trim() || null);
      episodeId.current = ep.id;
      const target = await uploadApi.createUrl(ep.id, selected.file);
      handle.current = uploadApi.put(target, selected.file, (loaded, total) => setProgress({ loaded, total }));
      await handle.current.promise;
      handle.current = null;
      setPhase('verifying');
      await uploadApi.complete(ep.id);
      episodeId.current = null;
      navigate(`/episodes/${ep.id}/processing`, { replace: true });
    } catch (e) {
      handle.current = null;
      if (e instanceof DOMException && e.name === 'AbortError') return;
      await cleanupEpisode();
      // 서버 검증 실패: 해당 파일을 오류 목록으로 옮긴다
      setRejected((r) => [...r, { ...selected, error: errorMessage(e, '업로드에 실패했어요.') }]);
      setSelected(null);
      setProgress(null);
      setPhase('empty');
    }
  };

  const cancel = async () => {
    handle.current?.abort();
    handle.current = null;
    await cleanupEpisode();
    setProgress(null);
    setPhase('ready');
  };

  const busy = phase === 'uploading' || phase === 'verifying';

  return (
    <div className="center-page">
      <div className="center-top" style={{ maxWidth: 680 }}>
        <Link to="/" className="back-link">
          <IconBack />
          프로젝트로
        </Link>
        <Brand size={14} />
      </div>

      <section aria-label="새 에피소드" className="panel-card" style={{ width: '100%', maxWidth: 680, display: 'flex', flexDirection: 'column', gap: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, letterSpacing: '-0.01em' }}>새 에피소드</h1>

        <label className="field">
          <span>
            에피소드 제목{' '}
            <span className="small muted" style={{ fontWeight: 400 }}>
              비워두면 분석 후 AI가 제목을 추천해요
            </span>
          </span>
          <input
            className="text-input"
            type="text"
            placeholder="예: EP.05 대운 이야기"
            value={title}
            maxLength={200}
            disabled={busy}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>

        {!selected && <FileDropzone onFiles={(f) => void pick(f)} disabled={busy || phase === 'checking'} />}
        {phase === 'checking' && <p className="small muted">파일을 확인하고 있어요…</p>}

        <RejectedFiles files={rejected} />

        {selected && (
          <SelectedFile
            file={selected}
            phase={phase === 'empty' ? 'ready' : phase}
            uploading={progress}
            onChange={phase === 'ready' ? () => setSelected(null) : undefined}
          />
        )}

        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
          <span className="small muted">업로드가 끝나면 자동으로 분석을 시작해요.</span>
          {phase === 'ready' && (
            <button type="button" className="btn btn-primary btn-lg" onClick={() => void start()}>
              업로드하고 분석 시작
            </button>
          )}
          {phase === 'uploading' && (
            <button type="button" className="btn btn-lg" onClick={() => void cancel()}>
              취소
            </button>
          )}
          {phase === 'empty' && rejected.length > 0 && (
            <span className="small" style={{ color: 'var(--ink-3)' }}>
              올바른 파일로 다시 선택해 주세요.
            </span>
          )}
        </div>
      </section>
    </div>
  );
}
