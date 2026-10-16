import type { JobAccepted, UploadUrlResponse } from '../types/episode';
import { api } from './client';

export interface UploadHandle {
  promise: Promise<void>;
  abort: () => void;
}

export const uploadApi = {
  createUrl: (episodeId: string, file: File) =>
    api
      .post<UploadUrlResponse>(`/api/episodes/${episodeId}/upload-url`, {
        filename: file.name,
        size: file.size,
        content_type: file.type || null,
      })
      .then((r) => r.data),

  complete: (episodeId: string) =>
    api.post<JobAccepted>(`/api/episodes/${episodeId}/upload-complete`, null, { timeout: 180_000 }).then((r) => r.data),

  /** Signed Upload URL로 Storage에 직접 올린다. 진행률을 받기 위해 XHR을 쓴다. */
  put(target: UploadUrlResponse, file: File, onProgress: (loaded: number, total: number) => void): UploadHandle {
    const xhr = new XMLHttpRequest();
    const promise = new Promise<void>((resolve, reject) => {
      xhr.open(target.method || 'PUT', target.upload_url);
      Object.entries(target.headers).forEach(([k, v]) => xhr.setRequestHeader(k, v));
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(e.loaded, e.total);
      };
      xhr.onload = () =>
        xhr.status >= 200 && xhr.status < 300
          ? resolve()
          : reject(new Error(`업로드에 실패했어요. (${xhr.status})`));
      xhr.onerror = () => reject(new Error('업로드 중 연결이 끊겼어요. 다시 시도해 주세요.'));
      xhr.onabort = () => reject(new DOMException('aborted', 'AbortError'));
      xhr.send(file);
    });
    return { promise, abort: () => xhr.abort() };
  },
};
