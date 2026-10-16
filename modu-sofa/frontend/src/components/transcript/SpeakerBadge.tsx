import { speakerInitial, speakerName, speakerTint, type Speaker } from '../../types/speaker';

export function SpeakerBadge({ speaker }: { speaker: Speaker | undefined }) {
  if (!speaker) return <span className="small muted">알 수 없음</span>;
  if (!speaker.display_name) {
    // 이름이 없으면 speaker_code를 그대로 보여준다
    return (
      <span className="spk-badge code" style={{ background: speakerTint(speaker.color), color: speaker.color }}>
        <span>{speaker.speaker_code}</span>
      </span>
    );
  }
  return (
    <span className="spk-badge" style={{ background: speakerTint(speaker.color), color: speaker.color }} title={speakerName(speaker)}>
      <span className="spk-dot" aria-hidden="true" style={{ background: speaker.color }}>
        {speakerInitial(speaker)}
      </span>
      <span>{speakerName(speaker)}</span>
    </span>
  );
}

export function SpeakerAvatar({ speaker, size = 40 }: { speaker: Speaker; size?: number }) {
  return (
    <span
      className="spk-avatar"
      aria-hidden="true"
      style={{ background: speaker.display_name ? speaker.color : '#5F5D78', width: size, height: size, fontSize: size < 32 ? 12 : 14 }}
    >
      {speakerInitial(speaker)}
    </span>
  );
}
