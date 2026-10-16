import { useEffect, type RefObject } from 'react';
import { usePlayerStore } from '../store/playerStore';

/** <audio> 요소 이벤트를 playerStore에 연결한다. */
export function useAudioPlayer(ref: RefObject<HTMLAudioElement>, knownDuration?: number | null) {
  useEffect(() => {
    const audio = ref.current;
    if (!audio) return;
    const st = usePlayerStore.getState();
    st.setAudio(audio);
    audio.volume = st.volume;
    audio.playbackRate = st.rate;
    st._sync({ currentTime: 0, playing: false, stopAt: null });

    const onTime = () => {
      const { stopAt, skipRanges, skipIgnoreStart } = usePlayerStore.getState();
      // 재생 중 잘라낸 구간에 들어가면 끝으로 건너뛴다 (내보낸 파일과 같은 흐름으로 미리 듣기)
      if (!audio.paused) {
        const hit = skipRanges.find((r) => audio.currentTime >= r.start_time && audio.currentTime < r.end_time - 0.05);
        if (!hit && skipIgnoreStart != null) usePlayerStore.getState()._sync({ skipIgnoreStart: null });
        if (hit && hit.start_time !== skipIgnoreStart) {
          audio.currentTime = hit.end_time;
          return;
        }
      }
      if (stopAt != null && audio.currentTime >= stopAt) {
        audio.pause();
        usePlayerStore.getState()._sync({ stopAt: null, currentTime: audio.currentTime });
        return;
      }
      usePlayerStore.getState()._sync({ currentTime: audio.currentTime });
    };
    const onPlay = () => usePlayerStore.getState()._sync({ playing: true });
    const onPause = () => usePlayerStore.getState()._sync({ playing: false });
    const onMeta = () => {
      if (Number.isFinite(audio.duration)) usePlayerStore.getState()._sync({ duration: audio.duration });
    };

    audio.addEventListener('timeupdate', onTime);
    audio.addEventListener('seeked', onTime);
    audio.addEventListener('play', onPlay);
    audio.addEventListener('pause', onPause);
    audio.addEventListener('ended', onPause);
    audio.addEventListener('loadedmetadata', onMeta);
    audio.addEventListener('durationchange', onMeta);
    return () => {
      audio.pause();
      audio.removeEventListener('timeupdate', onTime);
      audio.removeEventListener('seeked', onTime);
      audio.removeEventListener('play', onPlay);
      audio.removeEventListener('pause', onPause);
      audio.removeEventListener('ended', onPause);
      audio.removeEventListener('loadedmetadata', onMeta);
      audio.removeEventListener('durationchange', onMeta);
      if (usePlayerStore.getState().audio === audio) usePlayerStore.getState().setAudio(null);
    };
  }, [ref]);

  // 재생용 파일 기준 duration (메타데이터를 읽기 전에도 타임라인을 그릴 수 있게)
  useEffect(() => {
    const audio = ref.current;
    if (knownDuration && !(audio && Number.isFinite(audio.duration))) {
      usePlayerStore.getState()._sync({ duration: knownDuration });
    }
  }, [ref, knownDuration]);
}
