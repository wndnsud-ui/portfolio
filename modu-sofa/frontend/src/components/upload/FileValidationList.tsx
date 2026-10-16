import type { CheckedFile } from '../../utils/fileValidation';
import { fmtMB, fmtTime } from '../../utils/format';
import { IconCheck, IconMusic, IconX } from '../common/Icons';

export function RejectedFiles({ files }: { files: CheckedFile[] }) {
  if (!files.length) return null;
  return (
    <div role="alert" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {files.map((f, i) => (
        <div key={`${f.file.name}-${i}`} className="file-error">
          <span className="x-dot" aria-hidden="true">
            <IconX stroke="#FFFFFF" />
          </span>
          <span style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span style={{ fontWeight: 600, overflowWrap: 'anywhere' }}>
              {f.file.name}{' '}
              {f.duration != null && (
                <span className="mono xsmall muted" style={{ fontWeight: 400 }}>
                  {fmtTime(f.duration)}
                </span>
              )}
            </span>
            <span className="small" style={{ color: 'var(--danger-ink)' }}>
              {f.error}
            </span>
          </span>
        </div>
      ))}
    </div>
  );
}

interface SelectedProps {
  file: CheckedFile;
  onChange?: () => void;
  uploading?: { loaded: number; total: number } | null;
  phase?: 'checking' | 'ready' | 'uploading' | 'verifying';
}

const Ok = () => <IconCheck stroke="#166534" />;
const Pending = () => (
  <span aria-hidden="true" style={{ width: 16, height: 16, borderRadius: '50%', border: '2px solid #CBC7DE', display: 'inline-block' }} />
);

export function SelectedFile({ file, onChange, uploading, phase = 'ready' }: SelectedProps) {
  const pct = uploading && uploading.total ? Math.round((uploading.loaded / uploading.total) * 100) : 0;
  return (
    <div className="file-box">
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <span className="file-icon" aria-hidden="true">
          <IconMusic stroke="#4A2FD0" />
        </span>
        <span style={{ flex: 1, minWidth: 0, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {file.file.name}
        </span>
        {onChange && (
          <button type="button" className="btn btn-xs" style={{ height: 36 }} onClick={onChange}>
            다른 파일
          </button>
        )}
      </div>
      <ul className="checks">
        <li>
          <Ok />
          형식 <b>{file.ext.toUpperCase()}</b>
        </li>
        <li>
          {file.duration != null ? <Ok /> : <Pending />}
          길이{' '}
          {file.duration != null ? (
            <>
              <b className="mono">{fmtTime(file.duration)}</b> <span className="muted">/ 90:00</span>
            </>
          ) : (
            <span className="muted">업로드 후 서버에서 확인</span>
          )}
        </li>
        <li>
          <Ok />
          용량 <b className="mono">{fmtMB(file.file.size)}</b> <span className="muted">/ 500MB</span>
        </li>
        <li>
          {file.playable ? <Ok /> : <Pending />}
          {file.playable ? '재생 가능 확인' : '재생 가능 여부는 서버에서 확인'}
        </li>
      </ul>
      {phase === 'uploading' && uploading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span className="progress" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="업로드 진행률">
            <span style={{ width: `${pct}%` }} />
          </span>
          <span className="xsmall" style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--ink-3)' }}>
            <span>업로드 중 · {pct}%</span>
            <span className="mono">
              {(uploading.loaded / 1024 / 1024).toFixed(1)} / {(uploading.total / 1024 / 1024).toFixed(1)} MB
            </span>
          </span>
        </div>
      )}
      {phase === 'verifying' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span className="progress indeterminate">
            <span />
          </span>
          <span className="xsmall" style={{ color: 'var(--ink-3)' }}>
            서버에서 형식 · 길이 · 재생 가능 여부를 확인하고 있어요
          </span>
        </div>
      )}
    </div>
  );
}
