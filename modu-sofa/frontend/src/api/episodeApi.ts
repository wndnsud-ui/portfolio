import type { Episode, EpisodeDetail, PeaksDoc } from '../types/episode';
import { api } from './client';

export const episodeApi = {
  list: () => api.get<Episode[]>('/api/episodes').then((r) => r.data),
  get: (id: string) => api.get<EpisodeDetail>(`/api/episodes/${id}`).then((r) => r.data),
  create: (title: string | null) => api.post<Episode>('/api/episodes', { title }).then((r) => r.data),
  update: (id: string, body: { title?: string | null; description?: string | null }) =>
    api.patch<Episode>(`/api/episodes/${id}`, body).then((r) => r.data),
  remove: (id: string) => api.delete(`/api/episodes/${id}`),
  peaks: (url: string) => fetch(url).then((r) => (r.ok ? (r.json() as Promise<PeaksDoc>) : null)),
};
