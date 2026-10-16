import { usePlayerStore } from '../../store/playerStore';
import { fmtTime } from '../../utils/format';
import { IconBack10, IconFwd10, IconPauseBig, IconPlayBig } from '../common/Icons';

const SPEEDS = [1, 1.25, 1.5, 2];

export function PlaybackControls({ duration }: { duration: number }) {
  const currentTime = usePlayerStore((s) => s.currentTime);
  const playing = usePlayerStore((s) => s.playing);
  const rate = usePlayerStore((s) => s.rate);
  const toggle = usePlayerStore((s) => s.toggle);
  const skip = usePlayerStore((s) => s.skip);
  const setRate = usePlayerStore((s) => s.setRate);

  return (
    <div className="player-controls">
      <span className="player-time" aria-live="off">
        <b style={{ fontWeight: 500 }}>{fmtTime(currentTime)}</b> <span className="muted">/ {fmtTime(duration)}</span>
      </span>
      <button type="button" className="icon-btn" aria-label="10초 뒤로" onClick={() => skip(-10)}>
        <IconBack10 />
      </button>
      <button type="button" className="play-btn" aria-label={playing ? '일시정지' : '재생'} onClick={toggle}>
        {playing ? <IconPauseBig /> : <IconPlayBig />}
      </button>
      <button type="button" className="icon-btn" aria-label="10초 앞으로" onClick={() => skip(10)}>
        <IconFwd10 />
      </button>
      <button
        type="button"
        className="speed-btn"
        aria-label={`재생 속도 ${rate}배`}
        onClick={() => setRate(SPEEDS[(SPEEDS.indexOf(rate) + 1) % SPEEDS.length])}
      >
        {rate}x
      </button>
    </div>
  );
}
