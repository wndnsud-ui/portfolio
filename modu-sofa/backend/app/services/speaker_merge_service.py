import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import bad_request, conflict, not_found
from app.models import Episode, EpisodeSpeaker, SpeakerMerge, TranscriptSegment
from app.repositories import speaker_repo
from app.schemas.speaker import LastMergeOut, SpeakerOut, SpeakersOut, SpeakerUpdate


def list_speakers(db: Session, ep: Episode) -> SpeakersOut:
    speakers = speaker_repo.list_for_episode(db, ep.id)
    stats = speaker_repo.stats(db, ep.id)
    total = sum(s["count"] for s in stats.values()) or 1
    multi_chunk = (ep.duration or 0) > settings.STT_CHUNK_SEC
    first_boundary = settings.STT_CHUNK_SEC - settings.STT_OVERLAP_SEC
    out = []
    for sp in speakers:
        st = stats.get(sp.id, {"count": 0, "sample": None})
        sample = st["sample"]
        first_start = st.get("first_start")
        share = st["count"] / total
        # 첫 청크 이후에 처음 등장했거나 비중이 아주 작은 화자는 같은 사람이 둘로 나뉘었을 가능성이 있다.
        suspect = len(speakers) > 1 and (
            (multi_chunk and first_start is not None and first_start >= first_boundary) or share < 0.05
        )
        out.append(
            SpeakerOut(
                id=sp.id,
                speaker_code=sp.speaker_code,
                display_name=sp.display_name,
                color=sp.color,
                segment_count=st["count"],
                share=round(share, 4),
                sample_start=sample[0] if sample else None,
                sample_end=sample[1] if sample else None,
                first_start=first_start,
                suspect=suspect,
            )
        )
    lm = speaker_repo.last_merge(db, ep.id)
    last = (
        LastMergeOut(
            from_speaker_code=lm.from_speaker_code,
            from_display_name=lm.from_display_name,
            into_speaker_id=lm.into_speaker_id,
            segment_count=len(lm.segment_ids or []),
        )
        if lm
        else None
    )
    return SpeakersOut(speakers=out, last_merge=last)


def update_speaker(db: Session, sp: EpisodeSpeaker, body: SpeakerUpdate) -> Episode:
    if "display_name" in body.model_fields_set:
        sp.display_name = (body.display_name or "").strip() or None
    if body.color:
        sp.color = body.color
    db.commit()
    return db.get(Episode, sp.episode_id)


def merge(db: Session, ep: Episode, from_id: uuid.UUID, into_id: uuid.UUID) -> None:
    """from 화자의 Segment를 모두 into로 옮기고 from 화자를 삭제한다. 옮긴 Segment ID는 되돌리기용으로 보관."""
    if from_id == into_id:
        raise bad_request("같은 화자끼리는 병합할 수 없어요.")
    src = speaker_repo.get_in_episode(db, from_id, ep.id)
    dst = speaker_repo.get_in_episode(db, into_id, ep.id)
    if not src or not dst:
        raise not_found()
    seg_ids = list(
        db.scalars(
            select(TranscriptSegment.id).where(
                TranscriptSegment.episode_id == ep.id, TranscriptSegment.speaker_id == src.id
            )
        )
    )
    db.execute(
        update(TranscriptSegment)
        .where(TranscriptSegment.episode_id == ep.id, TranscriptSegment.speaker_id == src.id)
        .values(speaker_id=dst.id)
    )
    db.add(
        SpeakerMerge(
            episode_id=ep.id,
            from_speaker_id=src.id,
            from_speaker_code=src.speaker_code,
            from_display_name=src.display_name,
            from_color=src.color,
            into_speaker_id=dst.id,
            segment_ids=[str(i) for i in seg_ids],
        )
    )
    db.delete(src)
    db.commit()


def undo_last(db: Session, ep: Episode) -> None:
    lm = speaker_repo.last_merge(db, ep.id)
    if not lm:
        raise conflict("되돌릴 병합이 없어요.", "nothing_to_undo")
    if speaker_repo.get_in_episode(db, lm.into_speaker_id, ep.id) is None:
        raise conflict("병합한 화자가 이미 바뀌어 되돌릴 수 없어요.", "cannot_undo")
    restored = EpisodeSpeaker(
        id=lm.from_speaker_id,
        episode_id=ep.id,
        speaker_code=lm.from_speaker_code,
        display_name=lm.from_display_name,
        color=lm.from_color,
    )
    db.add(restored)
    db.flush()
    ids = [uuid.UUID(i) for i in (lm.segment_ids or [])]
    if ids:
        db.execute(
            update(TranscriptSegment)
            .where(
                TranscriptSegment.episode_id == ep.id,
                TranscriptSegment.id.in_(ids),
                TranscriptSegment.speaker_id == lm.into_speaker_id,
            )
            .values(speaker_id=restored.id)
        )
    db.delete(lm)
    db.commit()
