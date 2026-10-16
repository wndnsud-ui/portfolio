import { useRef, useState, type ReactNode } from 'react';
import { ACCEPT } from '../../utils/fileValidation';
import { IconUpload } from '../common/Icons';

interface Props {
  onFiles: (files: File[]) => void;
  variant?: 'wide' | 'box';
  disabled?: boolean;
  children?: ReactNode;
}

export function FileDropzone({ onFiles, variant = 'box', disabled }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  const dropHandlers = {
    onDragOver: (e: React.DragEvent) => {
      if (disabled) return;
      e.preventDefault();
      setOver(true);
    },
    onDragLeave: () => setOver(false),
    onDrop: (e: React.DragEvent) => {
      e.preventDefault();
      setOver(false);
      if (disabled) return;
      const files = Array.from(e.dataTransfer.files);
      if (files.length) onFiles(files);
    },
  };

  const picker = (
    <input
      ref={input}
      type="file"
      accept={ACCEPT}
      multiple
      hidden
      onChange={(e) => {
        const files = Array.from(e.target.files ?? []);
        e.target.value = '';
        if (files.length) onFiles(files);
      }}
    />
  );

  if (variant === 'wide') {
    return (
      <>
        <button
          type="button"
          className={`dropzone-wide${over ? ' over' : ''}`}
          onClick={() => input.current?.click()}
          disabled={disabled}
          {...dropHandlers}
        >
          <span className="dz-icon" aria-hidden="true">
            <IconUpload size={26} />
          </span>
          <span style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span style={{ fontSize: 16, fontWeight: 600 }}>음성 파일을 끌어다 놓거나 클릭해서 업로드</span>
            <span className="muted">MP3 · WAV · M4A · 최대 90분 · 업로드하면 화자별 Transcript를 자동으로 만들어요</span>
          </span>
        </button>
        {picker}
      </>
    );
  }

  return (
    <div className={`dropzone${over ? ' over' : ''}`} {...dropHandlers}>
      <IconUpload size={28} stroke="#4A2FD0" />
      <span style={{ fontWeight: 600 }}>
        음성 파일을 끌어다 놓거나{' '}
        <button
          type="button"
          disabled={disabled}
          onClick={() => input.current?.click()}
          style={{ border: 0, background: 'transparent', padding: 0, color: 'var(--primary-ink)', fontWeight: 600, textDecoration: 'underline' }}
        >
          파일 선택
        </button>
      </span>
      <span style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 6 }}>
        <span className="chip">MP3 · WAV · M4A</span>
        <span className="chip">최대 90분</span>
        <span className="chip">최대 500MB</span>
      </span>
      {picker}
    </div>
  );
}
