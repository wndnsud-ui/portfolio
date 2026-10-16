import { useCallback, useEffect, useState } from 'react';
import { errorMessage } from '../../api/client';
import { editApi } from '../../api/editApi';
import { useEpisodePolling } from '../../hooks/useEpisodePolling';
import { cutTotal, type Cut, type ExportJob, type ExportOptions, type IntroClip } from '../../types/edit';
import { fmtMB, fmtTime, parseServerDate } from '../../utils/format';
import { Dialog } from '../common/Dialog';
import { IconSparkle } from '../common/Icons';
import { toastError } from '../common/toastStore';

interface Props {
  episodeId: string;
  cuts: Cut[];
  onClose: () => void;
}

const ago = (iso: string) => {
  const m = Math.floor((Date.now() - parseServerDate(iso).getTime()) / 60000);
  if (m < 1) return '방금';
  if (m < 60) return `${m}분 전`;
  if (m < 1440) return `${Math.floor(m / 60)}시간 전`;
  return `${Math.floor(m / 1440)}일 전`;
};

const optionSummary = (o: ExportOptions) =>
  [o.apply_cuts && '자르기', o.enhance && '음량·잡음 보정', o.ai_denoise && 'AI 잡음 제거', o.intro_id && '시작음']
    .filter(Boolean)
    .join(' · ') || '원본 그대로';

export function ExportDialog({ episodeId, cuts, onClose }: Props) {
  const [opts, setOpts] = useState<ExportOptions>({
    apply_cuts: cuts.length > 0,
    enhance: true,
    ai_denoise: false,
    intro_id: null,
  });
  const [jobs, setJobs] = useState<ExportJob[]>([]);
  const [intros, setIntros] = useState<IntroClip[]>([]);
  const [prompt, setPrompt] = useState('');
  const [provider, setProvider] = useState('');
  const [seconds, setSeconds] = useState(8);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [j, i] = await Promise.all([editApi.exports(episodeId), editApi.intros()]);
    setJobs(j);
    setIntros(i);
  }, [episodeId]);

  useEffect(() => {
    void refresh();
    void editApi.introPrompt(episodeId).then((p) => {
      setPrompt(p.prompt);
      setProvider(p.provider);
    });
  }, [episodeId, refresh]);

  const running = jobs.some((j) => j.status === 'running') || intros.some((i) => i.status === 'running');
  useEpisodePolling(running, refresh, 2500);

  const set = (patch: Partial<ExportOptions>) => setOpts((o) => ({ ...o, ...patch }));

  const startExport = async () => {
    setBusy(true);
    try {
      await editApi.createExport(episodeId, opts);
      await refresh();
    } catch (e) {
      toastError(errorMessage(e, '내보내기를 시작하지 못했어요.'));
    } finally {
      setBusy(false);
    }
  };

  const makeIntro = async () => {
    try {
      const clip = await editApi.createIntro(prompt, seconds);
      set({ intro_id: clip.id });
      await refresh();
    } catch (e) {
      toastError(errorMessage(e, '시작음을 만들지 못했어요.'));
    }
  };

  const download = async (id: string) => {
    try {
      window.location.href = await editApi.downloadUrl(episodeId, id);
    } catch (e) {
      toastError(errorMessage(e, '다운로드 링크를 만들지 못했어요.'));
    }
  };

  const removeIntro = async (id: string) => {
    try {
      await editApi.deleteIntro(id);
      if (opts.intro_id === id) set({ intro_id: null });
    } catch (e) {
      toastError(errorMessage(e, '삭제하지 못했어요.'));
    }
    await refresh();
  };

  const removeExport = async (id: string) => {
    try {
      await editApi.deleteExport(episodeId, id);
    } catch (e) {
      toastError(errorMessage(e, '삭제하지 못했어요.'));
    }
    await refresh();
  };

  const selectedIntro = intros.find((i) => i.id === opts.intro_id);
  const introNotReady = !!opts.intro_id && selectedIntro?.status !== 'completed';
  const exportRunning = jobs.some((j) => j.status === 'running');

  return (
    <Dialog
      wide
      title="오디오 내보내기"
      description="원본은 그대로 두고, 선택한 처리를 적용한 새 MP3 파일을 만들어요."
      onClose={onClose}
      actions={
        <>
          <button type="button" className="btn" onClick={onClose}>
            닫기
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => void startExport()}
            disabled={busy || exportRunning || introNotReady}
          >
            {exportRunning ? '내보내는 중…' : 'MP3로 내보내기'}
          </button>
        </>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <label className="opt-row">
          <input
            type="checkbox"
            checked={opts.apply_cuts}
            disabled={!cuts.length}
            onChange={(e) => set({ apply_cuts: e.target.checked })}
          />
          <span style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span style={{ fontWeight: 600 }}>잘라낸 구간 적용</span>
            <span className="small muted">
              {cuts.length
                ? `${cuts.length}개 구간, 총 ${fmtTime(cutTotal(cuts))}을 빼고 이어 붙여요.`
                : '잘라낸 구간이 없어요. 에디터 상단의 자르기에서 만들 수 있어요.'}
            </span>
          </span>
        </label>

        <label className="opt-row">
          <input type="checkbox" checked={opts.enhance} onChange={(e) => set({ enhance: e.target.checked })} />
          <span style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span style={{ fontWeight: 600 }}>음량 맞추기 · 잡음 제거</span>
            <span className="small muted">
              팟캐스트 표준 음량(-16 LUFS)으로 맞추고, 웅웅거림과 배경 잡음을 줄이고, 목소리를 또렷하게 해요.
            </span>
          </span>
        </label>

        <label className="opt-row">
          <input type="checkbox" checked={opts.ai_denoise} onChange={(e) => set({ ai_denoise: e.target.checked })} />
          <span style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span style={{ fontWeight: 600 }}>
              AI 잡음 제거 <span className="pill pill-primary">고급</span>
            </span>
            <span className="small muted">
              신경망(RNNoise)이 생활 소음·키보드 소리를 강하게 걸러내요. 시간이 더 걸리고, 음악이 섞인 구간은 소리가 뭉개질 수 있어요.
            </span>
          </span>
        </label>

        <div className="opt-row" style={{ flexDirection: 'column', gap: 10 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <IconSparkle size={18} stroke="#5B3FE0" />
            <span style={{ fontWeight: 600 }}>AI 시작음</span>
            {provider === 'mock' && <span className="pill pill-warn">모의 (합성 차임)</span>}
          </span>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8 }} className="small">
            <input type="radio" name="intro" checked={!opts.intro_id} onChange={() => set({ intro_id: null })} />
            시작음 없이
          </label>
          {intros.map((i) => (
            <div key={i.id} className={`intro-item${opts.intro_id === i.id ? ' on' : ''}`}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }} className="small">
                <label style={{ flex: 1, display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  <input
                    type="radio"
                    name="intro"
                    checked={opts.intro_id === i.id}
                    disabled={i.status === 'failed'}
                    onChange={() => set({ intro_id: i.id })}
                  />
                  <span style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <span>
                      {i.status === 'running' && <span className="pill pill-primary">만드는 중</span>}
                      {i.status === 'failed' && <span style={{ color: 'var(--danger-ink)' }}>실패: {i.error_message}</span>}
                      {i.status === 'completed' && <b className="mono">{fmtTime(i.duration)}</b>}{' '}
                      <span className="muted">· {ago(i.created_at)}</span>
                    </span>
                    <span className="xsmall muted">{i.prompt}</span>
                  </span>
                </label>
                <button type="button" className="btn-link" disabled={i.status === 'running'} onClick={() => void removeIntro(i.id)}>
                  삭제
                </button>
              </div>
              {i.preview_url && <audio controls preload="none" src={i.preview_url} />}
            </div>
          ))}
          <label className="field small" style={{ fontWeight: 500, width: '100%' }}>
            새 시작음 설명 (AI에게 전달돼요)
            <textarea
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              style={{ width: '100%', padding: '8px 10px', border: '1px solid var(--line-input)', borderRadius: 8, resize: 'vertical', fontWeight: 400 }}
            />
          </label>
          <span style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
            <label className="small select-wrap" style={{ height: 36 }}>
              길이
              <select value={seconds} onChange={(e) => setSeconds(Number(e.target.value))}>
                {[5, 8, 12, 15, 20].map((s) => (
                  <option key={s} value={s}>
                    {s}초
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="btn btn-soft btn-sm"
              onClick={() => void makeIntro()}
              disabled={prompt.trim().length < 3 || intros.some((i) => i.status === 'running')}
            >
              <IconSparkle size={14} />
              AI로 시작음 만들기
            </button>
            {provider === 'mock' && (
              <span className="xsmall muted">ELEVENLABS_API_KEY를 넣으면 실제 AI 음악으로 만들어요.</span>
            )}
          </span>
        </div>
      </div>

      {jobs.length > 0 && (
        <div>
          <p className="small" style={{ fontWeight: 600, marginBottom: 4 }}>
            내보낸 파일
          </p>
          {jobs.map((j) => (
            <div key={j.id} className="export-row">
              <span style={{ flex: '1 1 240px', display: 'flex', flexDirection: 'column' }}>
                <span className="small">
                  {j.status === 'running' && <span className="pill pill-primary">만드는 중</span>}
                  {j.status === 'failed' && <span className="pill pill-danger">실패</span>}
                  {j.status === 'completed' && (
                    <b className="mono">
                      {fmtTime(j.duration)} · {fmtMB(j.file_size)}
                    </b>
                  )}{' '}
                  <span className="muted">{ago(j.created_at)}</span>
                </span>
                <span className="xsmall muted">{j.status === 'failed' ? j.error_message : optionSummary(j.options)}</span>
              </span>
              {j.status === 'completed' && (
                <button type="button" className="btn btn-primary btn-sm" onClick={() => void download(j.id)}>
                  다운로드
                </button>
              )}
              {j.status !== 'running' && (
                <button type="button" className="btn btn-sm" onClick={() => void removeExport(j.id)}>
                  삭제
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </Dialog>
  );
}
