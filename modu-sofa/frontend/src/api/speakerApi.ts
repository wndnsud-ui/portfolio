import type { SpeakersResponse } from '../types/speaker';
import { api } from './client';

export const speakerApi = {
  list: (episodeId: string) => api.get<SpeakersResponse>(`/api/episodes/${episodeId}/speakers`).then((r) => r.data),
  update: (speakerId: string, body: { display_name?: string | null; color?: string }) =>
    api.patch<SpeakersResponse>(`/api/speakers/${speakerId}`, body).then((r) => r.data),
  merge: (episodeId: string, fromId: string, intoId: string) =>
    api
      .post<SpeakersResponse>(`/api/episodes/${episodeId}/speakers/merge`, { from_id: fromId, into_id: intoId })
      .then((r) => r.data),
  undo: (episodeId: string) =>
    api.post<SpeakersResponse>(`/api/episodes/${episodeId}/speakers/merge/undo`).then((r) => r.data),
};
