import { useEffect, useRef, useState } from 'react';
import { episodeApi } from '../../api/episodeApi';
import { useAudioPlayer } from '../../hooks/useAudioPlayer';
import { usePlayerStore } from '../../store/playerStore';
import type { Chapter } from '../../types/ai';
import type { Cut } from '../../types/edit';
import type { PeaksDoc } from '../../types/episode';
import { IconVolume } from '../common/Icons';
import { PlaybackControls } from './PlaybackControls';
import { Waveform } from './Waveform';

interface Props {
  src: string | null;
  peaksUrl: string | null;
  duration: number;
  chapters: Chapter[];
  cuts: Cut[];
  onCutsChange: (cuts: Cut[]) => void;
  /** Signed URL 만료 등으로 재생 오류가 나면 호출 → 새 URL 발급 */
  onSourceError: () => void;
}

export function AudioPlayer({ src, peaksUrl, duration, chapters, cuts, onCutsChange, onSourceError }: Props) {
  const ref = useRef<HTMLAudioElement>(null);
  const [peaks, setPeaks] = useState<PeaksDoc | null>(null);
  const peaksKey = peaksUrl?.split('?')[0] ?? null;

  useAudioPlayer(ref, duration);

  useEffect(() => {
    if (!peaksUrl) return;
    let alive = true;
    episodeApi
      .peaks(peaksUrl)
      .then((p) => alive && setPeaks(p))
      .catch(() => alive && setPeaks(null));
    return () => {
      alive = false;
    };
    // Signed URL의 토큰이 바뀌어도 같은 파일이면 다시 받지 않는다
  }, [peaksKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // 재생 URL이 갱신되면 재생 위치를 유지한다
  const lastSrc = useRef<string | null>(null);
  useEffect(() => {
    const audio = ref.current;
    if (!audio || !src || lastSrc.current === src) return;
    const keep = lastSrc.current ? audio.currentTime : 0;
    const wasPlaying = lastSrc.current ? !audio.paused : false;
    lastSrc.current = src;
    audio.src = src;
    if (keep > 0) {
      const restore = () => {
        audio.currentTime = keep;
        if (wasPlaying) void audio.play().catch(() => undefined);
      };
      audio.addEventListener('loadedmetadata', restore, { once: true });
    }
  }, [src]);

  const volume = usePlayerStore((s) => s.volume);
  const setVolume = usePlayerStore((s) => s.setVolume);
  const currentTime = usePlayerStore((s) => s.currentTime);
  const seek = usePlayerStore((s) => s.seek);

  return (
    <div className="player" role="region" aria-label="오디오 플레이어">
      <audio ref={ref} preload="metadata" onError={onSourceError} />
      <PlaybackControls duration={duration} />
      <div style={{ flex: '1 1 420px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
        <Waveform peaks={peaks} duration={duration} chapters={chapters} cuts={cuts} onCutsChange={onCutsChange} />
        <label>
          <span className="sr-only">재생 위치</span>
          <input
            className="range"
            type="range"
            min={0}
            max={Math.max(1, Math.floor(duration))}
            step={1}
            value={Math.floor(currentTime)}
            onChange={(e) => seek(Number(e.target.value), !(ref.current?.paused ?? true))}
          />
        </label>
      </div>
      <label className="volume">
        <IconVolume />
        <span className="sr-only">볼륨</span>
        <input type="range" min={0} max={100} value={Math.round(volume * 100)} onChange={(e) => setVolume(Number(e.target.value) / 100)} />
      </label>
    </div>
  );
}
