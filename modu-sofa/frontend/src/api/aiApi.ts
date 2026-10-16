import type { AiResult } from '../types/ai';
import type { Episode, JobAccepted } from '../types/episode';
import { api } from './client';

export const aiApi = {
  get: (episodeId: string) => api.get<AiResult>(`/api/episodes/${episodeId}/ai`).then((r) => r.data),
  analyze: (episodeId: string) => api.post<JobAccepted>(`/api/episodes/${episodeId}/ai/analyze`).then((r) => r.data),
  selectTitle: (episodeId: string, title: string) =>
    api.post<Episode>(`/api/episodes/${episodeId}/ai/title`, { title }).then((r) => r.data),
};
