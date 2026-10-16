import { useEffect, useRef } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Brand } from '../components/common/Brand';
import { IconBack } from '../components/common/Icons';
import { SpeakerManager } from '../components/speaker/SpeakerManager';
import { useEpisodeStore } from '../store/episodeStore';

/** ⑥ 화자 이름 · 병합. 대표 구간 듣기는 이 화면 전용 <audio> 하나로 재생한다. */
export function SpeakersPage() {
  const { id = '' } = useParams();
  const load = useEpisodeStore((s) => s.load);
  const episode = useEpisodeStore((s) => s.episode);
  const speakers = useEpisodeStore((s) => s.speakers);
  const loadError = useEpisodeStore((s) => s.loadError);
  const audio = useRef<HTMLAudioElement>(null);
  const stopAt = useRef<number | null>(null);

  useEffect(() => {
    void load(id);
  }, [id, load]);

  const playSample = (start: number, end: number) => {
    const a = audio.current;
    if (!a) return;
    stopAt.current = end;
    a.currentTime = start;
    void a.play().catch(() => undefined);
  };

  return (
    <div className="center-page" style={{ gap: 24 }}>
      <div className="center-top" style={{ maxWidth: 760, flexWrap: 'wrap' }}>
        <Link to={`/episodes/${id}`} className="back-link">
          <IconBack />
          에디터로
        </Link>
        <Brand size={14} />
      </div>

      <section aria-label="화자 관리" className="panel-card" style={{ width: '100%', maxWidth: 760, padding: 28, display: 'flex', flexDirection: 'column', gap: 18 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>
          화자 <span className="muted" style={{ fontWeight: 500 }}>{speakers.length}명</span>
        </h1>
        {loadError ? <p className="muted">{loadError}</p> : episode?.id === id ? <SpeakerManager onPlaySample={playSample} /> : <p className="muted">불러오는 중…</p>}
      </section>

      {episode?.playback_url && (
        <audio
          ref={audio}
          src={episode.playback_url}
          preload="metadata"
          onTimeUpdate={(e) => {
            if (stopAt.current != null && e.currentTarget.currentTime >= stopAt.current) {
              e.currentTarget.pause();
              stopAt.current = null;
            }
          }}
        />
      )}
    </div>
  );
}
