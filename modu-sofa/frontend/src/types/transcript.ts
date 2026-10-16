import type { Speaker } from './speaker';

export interface Segment {
  id: string;
  speaker_id: string;
  seq: number;
  start_time: number;
  end_time: number;
  original_text: string;
  edited_text: string | null;
  is_deleted: boolean;
}

export interface Transcript {
  segments: Segment[];
  speakers: Speaker[];
  edited_count: number;
  deleted_count: number;
  named_speaker_count: number;
  merge_count: number;
}

export const segmentText = (s: Segment) => s.edited_text ?? s.original_text;
