export type EpisodeStatus =
  | 'created'
  | 'uploading'
  | 'uploaded'
  | 'processing'
  | 'transcribing'
  | 'transcribed'
  | 'failed';

export type AiStatus = 'none' | 'running' | 'completed' | 'failed';
export type ErrorStage = 'upload' | 'processing' | 'transcription' | 'ai';

export interface EpisodeCounts {
  speakers: number;
  chapters: number;
  highlights: number;
}

export interface Episode {
  id: string;
  title: string | null;
  description: string | null;
  original_filename: string | null;
  duration: number | null;
  file_size: number | null;
  status: EpisodeStatus;
  ai_status: AiStatus;
  error_stage: ErrorStage | null;
  error_message: string | null;
  progress_current: number;
  progress_total: number;
  /** "mock" = 모의 분석, 그 외 = 실제 STT 모델명 */
  stt_model: string | null;
  status_updated_at: string;
  created_at: string;
  updated_at: string;
  counts: EpisodeCounts | null;
}

export interface EpisodeDetail extends Episode {
  playback_url: string | null;
  peaks_url: string | null;
  stt_chunk_sec: number;
  stt_overlap_sec: number;
}

export interface JobAccepted {
  episode_id: string;
  status: EpisodeStatus;
  ai_status: AiStatus | null;
}

export interface UploadUrlResponse {
  upload_url: string;
  method: string;
  headers: Record<string, string>;
  path: string;
}

export interface PeaksDoc {
  version: number;
  points_per_sec: number;
  duration: number;
  data: number[];
}
