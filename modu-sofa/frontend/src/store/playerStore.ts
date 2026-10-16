import { create } from 'zustand';

/**
 * 재생 소스는 <audio> 하나. 모든 seek/play는 이 요소로만 한다.
 * Wavesurfer도 media 옵션으로 같은 요소에 연결된다.
 */
interface PlayerState {
  audio: HTMLAudioElement | null;
  currentTime: number;
  duration: number;
  playing: boolean;
  rate: number;
  volume: number;
  /** 하이라이트 구간 재생: 이 시각에 도달하면 멈춘다 */
  stopAt: number | null;
  /** 미리 듣기에서 건너뛸 구간 (잘라낸 구간) */
  skipRanges: { start_time: number; end_time: number }[];
  setSkipRanges: (r: { start_time: number; end_time: number }[]) => void;
  /** 사용자가 직접 이동해 들어간 잘린 구간은 건너뛰지 않는다 */
  skipIgnoreStart: number | null;
  setAudio: (el: HTMLAudioElement | null) => void;
  seek: (t: number, play?: boolean) => void;
  playRange: (start: number, end: number) => void;
  toggle: () => void;
  skip: (delta: number) => void;
  setRate: (r: number) => void;
  setVolume: (v: number) => void;
  _sync: (patch: Partial<PlayerState>) => void;
}

export const usePlayerStore = create<PlayerState>((set, get) => ({
  audio: null,
  currentTime: 0,
  duration: 0,
  playing: false,
  rate: 1,
  volume: 0.7,
  stopAt: null,
  skipRanges: [],
  skipIgnoreStart: null,
  setSkipRanges: (r) => set({ skipRanges: r }),

  setAudio: (el) => set({ audio: el }),

  seek: (t, play = true) => {
    const audio = get().audio;
    if (!audio) return;
    const dur = Number.isFinite(audio.duration) ? audio.duration : get().duration;
    const target = Math.max(0, Math.min(t, dur || t));
    audio.currentTime = target;
    const inCut = get().skipRanges.find((r) => target >= r.start_time && target < r.end_time);
    set({ currentTime: target, stopAt: null, skipIgnoreStart: inCut ? inCut.start_time : null });
    if (play) void audio.play().catch(() => undefined);
  },

  playRange: (start, end) => {
    get().seek(start, true);
    set({ stopAt: end });
  },

  toggle: () => {
    const audio = get().audio;
    if (!audio) return;
    if (audio.paused) {
      set({ stopAt: null });
      void audio.play().catch(() => undefined);
    } else audio.pause();
  },

  skip: (delta) => get().seek(get().currentTime + delta, !get().audio?.paused),

  setRate: (r) => {
    const audio = get().audio;
    if (audio) audio.playbackRate = r;
    set({ rate: r });
  },

  setVolume: (v) => {
    const audio = get().audio;
    if (audio) audio.volume = v;
    set({ volume: v });
  },

  _sync: (patch) => set(patch),
}));
