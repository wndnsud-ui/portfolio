"""음성 자르기(비파괴): 잘라낼 구간만 저장하고, 실제 자르기는 내보낼 때 한다."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import bad_request
from app.models import AudioCut, Episode, EpisodeStatus

MIN_CUT_SEC = 0.2
MAX_CUTS = 200


def normalize(ranges: list[tuple[float, float]], duration: float) -> list[tuple[float, float]]:
    """범위를 0~duration으로 자르고, 너무 짧은 구간은 버리고, 겹치거나 맞닿은 구간은 합친다."""
    cleaned = []
    for s, e in ranges:
        s, e = max(0.0, min(s, e)), min(duration, max(s, e))
        if e - s >= MIN_CUT_SEC:
            cleaned.append((round(s, 3), round(e, 3)))
    cleaned.sort()
    merged: list[tuple[float, float]] = []
    for s, e in cleaned:
        if merged and s <= merged[-1][1] + 0.01:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


def keep_ranges(cuts: list[tuple[float, float]], duration: float) -> list[tuple[float, float]]:
    out, t = [], 0.0
    for s, e in cuts:
        if s > t:
            out.append((t, s))
        t = max(t, e)
    if t < duration:
        out.append((t, duration))
    return out


def list_cuts(db: Session, episode_id) -> list[AudioCut]:
    return list(db.scalars(select(AudioCut).where(AudioCut.episode_id == episode_id).order_by(AudioCut.start_time)))


def replace_cuts(db: Session, ep: Episode, ranges: list[tuple[float, float]]) -> list[AudioCut]:
    if ep.status != EpisodeStatus.TRANSCRIBED or not ep.duration:
        raise bad_request("분석이 끝난 에피소드만 자를 수 있어요.", "not_ready")
    if len(ranges) > MAX_CUTS:
        raise bad_request(f"자를 구간은 {MAX_CUTS}개까지 만들 수 있어요.", "too_many_cuts")
    cuts = normalize(ranges, ep.duration)
    if sum(e - s for s, e in cuts) >= ep.duration - 1:
        raise bad_request("전체를 잘라낼 수는 없어요.", "cut_all")
    db.execute(delete(AudioCut).where(AudioCut.episode_id == ep.id))
    for s, e in cuts:
        db.add(AudioCut(episode_id=ep.id, start_time=s, end_time=e))
    db.commit()
    return list_cuts(db, ep.id)
