export interface Speaker {
  id: string;
  speaker_code: string;
  display_name: string | null;
  color: string;
  segment_count: number;
  share: number;
  sample_start: number | null;
  sample_end: number | null;
  first_start: number | null;
  suspect: boolean;
}

export interface LastMerge {
  from_speaker_code: string;
  from_display_name: string | null;
  into_speaker_id: string;
  segment_count: number;
}

export interface SpeakersResponse {
  speakers: Speaker[];
  last_merge: LastMerge | null;
}

export const speakerName = (s: Pick<Speaker, 'display_name' | 'speaker_code'>) =>
  s.display_name ?? s.speaker_code;

export const speakerInitial = (s: Pick<Speaker, 'display_name'>) =>
  s.display_name ? Array.from(s.display_name.trim())[0] ?? '?' : '?';

const TINTS: Record<string, string> = {
  '#B0124F': '#FCE4EE',
  '#1D4ED8': '#E3EBFD',
  '#15803D': '#E2F5E8',
  '#A04A06': '#FCEFD9',
  '#6D28D9': '#EDE5FD',
  '#0E7490': '#DDF3F7',
  '#B91C1C': '#FDE8E8',
  '#4D7C0F': '#ECF5DC',
  '#9D174D': '#FBE3EE',
  '#1E40AF': '#E2E9FB',
};

export const speakerTint = (color: string) =>
  TINTS[color.toUpperCase()] ?? `color-mix(in srgb, ${color} 12%, white)`;
