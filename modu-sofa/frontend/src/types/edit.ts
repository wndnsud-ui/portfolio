export interface Cut {
  id?: string;
  start_time: number;
  end_time: number;
}

export interface ExportOptions {
  apply_cuts: boolean;
  enhance: boolean;
  ai_denoise: boolean;
  intro_id: string | null;
}

export interface ExportJob {
  id: string;
  status: 'running' | 'completed' | 'failed';
  options: ExportOptions;
  duration: number | null;
  file_size: number | null;
  error_message: string | null;
  created_at: string;
}

export interface IntroClip {
  id: string;
  status: 'running' | 'completed' | 'failed';
  prompt: string;
  provider: string;
  duration: number | null;
  error_message: string | null;
  created_at: string;
  preview_url: string | null;
}

export const cutTotal = (cuts: Cut[]) => cuts.reduce((a, c) => a + (c.end_time - c.start_time), 0);

/** Segment가 잘린 구간에 얼마나 걸치는지: 'full' | 'partial' | null */
export function cutCoverage(start: number, end: number, cuts: Cut[]): 'full' | 'partial' | null {
  let covered = 0;
  for (const c of cuts) {
    covered += Math.max(0, Math.min(end, c.end_time) - Math.max(start, c.start_time));
  }
  const len = Math.max(0.001, end - start);
  if (covered >= len * 0.95) return 'full';
  return covered > 0.05 ? 'partial' : null;
}
