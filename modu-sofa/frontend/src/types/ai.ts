import type { AiStatus } from './episode';

export interface Chapter {
  id: string;
  start_segment_id: string;
  start_time: number;
  title: string;
  description: string | null;
  seq: number;
}

export interface Highlight {
  id: string;
  start_segment_id: string;
  end_segment_id: string;
  start_time: number;
  end_time: number;
  title: string;
  text: string;
  seq: number;
}

export interface AiResult {
  ai_status: AiStatus;
  error_message: string | null;
  summary: string | null;
  keywords: string[];
  title_candidates: string[];
  model: string | null;
  chapters: Chapter[];
  highlights: Highlight[];
}
