import type { Cut, ExportJob, ExportOptions, IntroClip } from '../types/edit';
import { api } from './client';

export const editApi = {
  cuts: (episodeId: string) => api.get<Cut[]>(`/api/episodes/${episodeId}/cuts`).then((r) => r.data),
  saveCuts: (episodeId: string, cuts: Cut[]) =>
    api
      .put<Cut[]>(`/api/episodes/${episodeId}/cuts`, {
        cuts: cuts.map((c) => ({ start_time: c.start_time, end_time: c.end_time })),
      })
      .then((r) => r.data),

  exports: (episodeId: string) => api.get<ExportJob[]>(`/api/episodes/${episodeId}/exports`).then((r) => r.data),
  createExport: (episodeId: string, opts: ExportOptions) =>
    api.post<ExportJob>(`/api/episodes/${episodeId}/exports`, opts).then((r) => r.data),
  downloadUrl: (episodeId: string, exportId: string) =>
    api.get<{ url: string }>(`/api/episodes/${episodeId}/exports/${exportId}/download`).then((r) => r.data.url),
  deleteExport: (episodeId: string, exportId: string) => api.delete(`/api/episodes/${episodeId}/exports/${exportId}`),

  introPrompt: (episodeId: string) =>
    api.get<{ prompt: string; provider: string }>(`/api/episodes/${episodeId}/intro-prompt`).then((r) => r.data),
  intros: () => api.get<IntroClip[]>('/api/intros').then((r) => r.data),
  createIntro: (prompt: string, seconds: number) =>
    api.post<IntroClip>('/api/intros', { prompt, seconds }).then((r) => r.data),
  deleteIntro: (id: string) => api.delete(`/api/intros/${id}`),
};
