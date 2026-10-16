export const MAX_MB = 500;
export const MAX_DURATION_SEC = 90 * 60;
export const ALLOWED_EXT = ['mp3', 'wav', 'm4a'] as const;
export const ACCEPT = '.mp3,.wav,.m4a,audio/mpeg,audio/wav,audio/x-wav,audio/mp4,audio/x-m4a';

// 11장 오류 문구
export const MSG = {
  format: '지원하지 않는 형식이에요. MP3, WAV, M4A 파일만 올릴 수 있어요.',
  long: '90분까지 올릴 수 있어요. 파일을 나눠서 올려 주세요.',
  large: '500MB까지 올릴 수 있어요.',
  unplayable: '파일을 재생할 수 없어요. 확장자는 맞지만 내용이 손상되었을 수 있어요.',
};

export interface CheckedFile {
  file: File;
  ext: string;
  /** 브라우저가 읽은 길이. 코덱을 지원하지 않으면 null (서버에서 다시 확인) */
  duration: number | null;
  /** true: 브라우저에서 재생 가능 확인, null: 브라우저가 판단 못 함(서버 확인) */
  playable: boolean | null;
  error: string | null;
}

export const extOf = (name: string) => (name.includes('.') ? name.split('.').pop()!.toLowerCase() : '');

function readDuration(file: File, timeoutMs = 8000): Promise<number | null> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const audio = new Audio();
    let done = false;
    const finish = (v: number | null) => {
      if (done) return;
      done = true;
      URL.revokeObjectURL(url);
      audio.removeAttribute('src');
      resolve(v);
    };
    audio.preload = 'metadata';
    audio.onloadedmetadata = () => finish(Number.isFinite(audio.duration) ? audio.duration : null);
    audio.onerror = () => finish(null);
    window.setTimeout(() => finish(null), timeoutMs);
    audio.src = url;
  });
}

/** 브라우저 1차 검증: 형식 · 용량 · (가능하면) 길이 */
export async function checkFile(file: File): Promise<CheckedFile> {
  const ext = extOf(file.name);
  const base: CheckedFile = { file, ext, duration: null, playable: null, error: null };
  if (!(ALLOWED_EXT as readonly string[]).includes(ext)) return { ...base, error: MSG.format };
  if (file.size > MAX_MB * 1024 * 1024) return { ...base, error: MSG.large };
  if (file.size === 0) return { ...base, error: MSG.unplayable };
  const duration = await readDuration(file);
  if (duration != null && duration > MAX_DURATION_SEC) return { ...base, duration, playable: true, error: MSG.long };
  return { ...base, duration, playable: duration != null ? true : null };
}
