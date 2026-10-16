import type { JobAccepted } from '../types/episode';
import type { Segment, Transcript } from '../types/transcript';
import { api } from './client';

export const transcriptApi = {
  get: (episodeId: string) => api.get<Transcript>(`/api/episodes/${episodeId}/transcript`).then((r) => r.data),
  cancel: (episodeId: string) => api.post<JobAccepted>(`/api/episodes/${episodeId}/cancel`).then((r) => r.data),
  reanalyze: (episodeId: string) => api.post<JobAccepted>(`/api/episodes/${episodeId}/transcribe`).then((r) => r.data),
  update: (segmentId: string, body: { edited_text?: string; speaker_id?: string }) =>
    api.patch<Segment>(`/api/transcripts/${segmentId}`, body).then((r) => r.data),
  revert: (segmentId: string) => api.post<Segment>(`/api/transcripts/${segmentId}/revert`).then((r) => r.data),
  remove: (segmentId: string) => api.delete<Segment>(`/api/transcripts/${segmentId}`).then((r) => r.data),
  restore: (segmentId: string) => api.post<Segment>(`/api/transcripts/${segmentId}/restore`).then((r) => r.data),
};
