"""STT 파이프라인.

전처리 → 청크별 STT(동시 2개 이하, 최대 3회 재시도) → offset 보정 → 겹침 제거 → 화자 통합 → 한 트랜잭션 저장.
"""

import json
import logging
import tempfile
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import reload_analysis_settings as settings_reload
from app.core.config import settings
from app.core.errors import MSG_NO_SPEECH, UserFacingError
from app.db.session import SessionLocal
from app.models import (
    AiStatus,
    EpisodeSpeaker,
    EpisodeStatus,
    ErrorStage,
    TranscriptSegment,
)
from app.repositories import ai_repo, episode_repo, segment_repo, speaker_repo
from app.services import audio_service, job_control, openai_client
from app.services.speaker_palette import code_for, color_for
from app.services.storage_service import episode_prefix, get_storage

log = logging.getLogger(__name__)


# ───────────────────────── 순수 로직 (테스트 대상) ─────────────────────────


@dataclass
class RawSegment:
    start: float  # 청크 기준
    end: float
    speaker: str
    text: str


@dataclass
class ChunkResult:
    index: int
    offset: float
    length: float
    segments: list[RawSegment]


@dataclass
class MergedSegment:
    start: float  # 전체 오디오 기준 (offset 보정 완료)
    end: float
    speaker: str  # SPEAKER_NN
    text: str


@dataclass
class _AbsSeg:
    start: float
    end: float
    raw: str
    text: str
    speaker: str | None = None


@dataclass
class MergeOutput:
    segments: list[MergedSegment]
    speaker_codes: list[str] = field(default_factory=list)


def parse_diarized(data: dict) -> list[RawSegment]:
    out = []
    for s in data.get("segments") or []:
        text = (s.get("text") or "").strip()
        if not text:
            continue
        st = float(s.get("start") or 0.0)
        en = float(s.get("end") or st)
        out.append(RawSegment(start=st, end=max(en, st), speaker=str(s.get("speaker") or "A"), text=text))
    return out


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def merge_chunks(chunks: list[ChunkResult], duration: float | None = None) -> MergeOutput:
    chunks = sorted(chunks, key=lambda c: c.index)
    abs_chunks: list[list[_AbsSeg]] = [
        # 7-4 offset 보정
        [_AbsSeg(s.start + c.offset, s.end + c.offset, s.speaker, s.text) for s in c.segments]
        for c in chunks
    ]

    codes: list[str] = []

    def new_code() -> str:
        code = code_for(len(codes))
        codes.append(code)
        return code

    # 첫 청크: 등장 순서대로 SPEAKER_01, 02 …
    first_map: dict[str, str] = {}
    for s in sorted(abs_chunks[0], key=lambda x: x.start) if abs_chunks else []:
        if s.raw not in first_map:
            first_map[s.raw] = new_code()
        s.speaker = first_map[s.raw]

    # 이후 청크: 겹침 구간에서 시간이 가장 많이 겹치는 화자끼리 매칭 (7-5 ②)
    for i in range(1, len(chunks)):
        prev_c, cur_c = chunks[i - 1], chunks[i]
        ov0, ov1 = cur_c.offset, prev_c.offset + prev_c.length
        score: dict[tuple[str, str], float] = defaultdict(float)
        if ov1 > ov0:
            for p in abs_chunks[i - 1]:
                if p.end <= ov0 or p.start >= ov1:
                    continue
                for c in abs_chunks[i]:
                    if c.end <= ov0 or c.start >= ov1:
                        continue
                    t = _overlap(max(p.start, ov0), min(p.end, ov1), max(c.start, ov0), min(c.end, ov1))
                    if t > 0:
                        score[(p.speaker or "", c.raw)] += t
        mapping: dict[str, str] = {}
        used: set[str] = set()
        for (g, r), t in sorted(score.items(), key=lambda kv: kv[1], reverse=True):
            if t < 0.5 or r in mapping or g in used or not g:
                continue
            mapping[r] = g
            used.add(g)
        for s in sorted(abs_chunks[i], key=lambda x: x.start):
            if s.raw not in mapping:
                mapping[s.raw] = new_code()  # 7-5 ③
            s.speaker = mapping[s.raw]

    # 겹침 제거: 겹침 구간의 중간 시각을 경계로 이전 청크는 경계 이전, 다음 청크는 경계 이후만 채택 (7-5 ①)
    merged: list[MergedSegment] = []
    for i, c in enumerate(chunks):
        lo = -1e18
        hi = 1e18
        if i > 0:
            prev = chunks[i - 1]
            lo = (c.offset + prev.offset + prev.length) / 2
        if i < len(chunks) - 1:
            nxt = chunks[i + 1]
            hi = (nxt.offset + c.offset + c.length) / 2
        for s in abs_chunks[i]:
            if lo <= s.start < hi:
                end = s.end if duration is None else min(s.end, duration)
                start = max(0.0, s.start)
                merged.append(MergedSegment(start=start, end=max(end, start), speaker=s.speaker or "", text=s.text))

    merged.sort(key=lambda m: (m.start, m.end))
    used_codes = []
    for m in merged:
        if m.speaker not in used_codes:
            used_codes.append(m.speaker)
    return MergeOutput(segments=merged, speaker_codes=sorted(used_codes))


# ───────────────────────── 파이프라인 ─────────────────────────

class ChunkFailed(Exception):
    def __init__(self, index: int, cause: Exception):
        super().__init__(f"chunk {index} failed: {cause}")
        self.index = index
        self.cause = cause


def _transcribe_with_retry(chunk: audio_service.ChunkFile, episode_id: uuid.UUID, gen: int) -> dict:
    last: Exception | None = None
    for attempt in range(settings.STT_MAX_RETRIES):
        if not job_control.stt_alive(episode_id, gen):
            raise job_control.Cancelled()
        try:
            return openai_client.transcribe_chunk(chunk.path, chunk.offset, chunk.length)
        except Exception as e:  # noqa: BLE001
            last = e
            log.warning("STT chunk %s attempt %s failed: %s", chunk.index, attempt + 1, e)
            if attempt < settings.STT_MAX_RETRIES - 1:
                time.sleep(2 ** (attempt + 1))
    raise ChunkFailed(chunk.index, last or RuntimeError("unknown"))


def run_pipeline(episode_id: uuid.UUID) -> None:
    """BackgroundTasks에서 호출. 호출 전에 episode_repo.claim()으로 status=processing 선점이 끝나 있어야 한다."""
    gen = job_control.start_stt(episode_id)
    try:
        _run_pipeline(episode_id, gen)
    except job_control.Cancelled:
        log.info("pipeline cancelled: %s", episode_id)


def _fail(episode_id: uuid.UUID, gen: int, stage: str, message: str) -> None:
    with SessionLocal() as db:
        ep = episode_repo.get(db, episode_id)
        # 취소된 작업은 상태를 덮어쓰지 않는다
        if ep and job_control.stt_alive(episode_id, gen):
            episode_repo.set_status(db, ep, EpisodeStatus.FAILED, error_stage=stage, error_message=message)


def _check(episode_id: uuid.UUID, gen: int) -> None:
    if not job_control.stt_alive(episode_id, gen):
        raise job_control.Cancelled()


def _run_pipeline(episode_id: uuid.UUID, gen: int) -> None:
    settings_reload()
    storage = get_storage()
    with SessionLocal() as db:
        ep = episode_repo.get(db, episode_id)
        if not ep or ep.status != EpisodeStatus.PROCESSING or not ep.original_path:
            return
        prefix = episode_prefix(ep.user_id, ep.id)
        original_path = ep.original_path

    with tempfile.TemporaryDirectory(prefix="modu-sofa-") as tmp:
        workdir = Path(tmp)
        # 1) 전처리
        try:
            pre = audio_service.preprocess(storage, prefix, original_path, workdir)
        except Exception as e:  # noqa: BLE001
            _check(episode_id, gen)
            log.exception("preprocess failed")
            _fail(episode_id, gen, ErrorStage.PROCESSING, f"오디오를 준비하지 못했어요. ({type(e).__name__})")
            return

        with SessionLocal() as db:
            ep = episode_repo.get(db, episode_id)
            if not ep:
                return
            _check(episode_id, gen)
            ep.playback_path = pre.playback_path
            ep.peaks_path = pre.peaks_path
            ep.duration = pre.duration
            episode_repo.set_status(
                db, ep, EpisodeStatus.TRANSCRIBING, progress_current=0, progress_total=len(pre.chunks)
            )

        # 2) 청크별 STT
        results: list[ChunkResult] = []
        done = 0
        try:
            with ThreadPoolExecutor(max_workers=max(1, min(2, settings.STT_CONCURRENCY))) as pool:
                futs = {pool.submit(_transcribe_with_retry, c, episode_id, gen): c for c in pre.chunks}
                for fut in as_completed(futs):
                    c = futs[fut]
                    if not job_control.stt_alive(episode_id, gen):
                        pool.shutdown(wait=False, cancel_futures=True)  # 아직 시작 안 한 구간은 보내지 않는다
                        raise job_control.Cancelled()
                    data = fut.result()
                    try:
                        storage.upload_bytes(
                            f"{prefix}/stt_raw/chunk_{c.index:02d}.json",
                            json.dumps(data, ensure_ascii=False).encode(),
                            "application/json",
                        )
                    except Exception:  # noqa: BLE001 - 디버깅용 보관 실패는 무시
                        log.warning("failed to store raw stt json", exc_info=True)
                    results.append(ChunkResult(c.index, c.offset, c.length, parse_diarized(data)))
                    done += 1
                    with SessionLocal() as db:
                        ep = episode_repo.get(db, episode_id)
                        if ep and job_control.stt_alive(episode_id, gen):
                            ep.progress_current = done
                            db.commit()
        except job_control.Cancelled:
            raise
        except ChunkFailed as e:
            _fail(
                episode_id,
                gen,
                ErrorStage.TRANSCRIPTION,
                f"구간 {e.index + 1}를 처리하지 못했어요. 업로드한 파일은 그대로 있으니 다시 시도할 수 있어요.",
            )
            return
        except Exception as e:  # noqa: BLE001
            log.exception("stt failed")
            _fail(episode_id, gen, ErrorStage.TRANSCRIPTION, f"음성 분석 중 오류가 발생했습니다. ({type(e).__name__})")
            return

    # 3) 통합 + 저장
    try:
        merged = merge_chunks(results, pre.duration)
        if not merged.segments:
            raise UserFacingError(MSG_NO_SPEECH, "no_speech")
        _save(episode_id, gen, merged)
    except job_control.Cancelled:
        raise
    except UserFacingError as e:
        _fail(episode_id, gen, ErrorStage.TRANSCRIPTION, e.message)
        return
    except Exception as e:  # noqa: BLE001
        log.exception("save failed")
        _fail(episode_id, gen, ErrorStage.TRANSCRIPTION, f"Transcript를 저장하지 못했어요. ({type(e).__name__})")
        return

    # 4) AI 분석 자동 시작
    from app.services import summary_service

    with SessionLocal() as db:
        claimed = episode_repo.claim_ai(db, episode_id)
    if claimed:
        summary_service.run_analysis(episode_id)


def _save(episode_id: uuid.UUID, gen: int, merged: MergeOutput) -> None:
    with SessionLocal() as db:
        ep = episode_repo.get(db, episode_id)
        if not ep:
            return
        # 취소됐으면 기존 대본을 지우지 않는다
        _check(episode_id, gen)
        if ep.status != EpisodeStatus.TRANSCRIBING:
            raise job_control.Cancelled()
        # 재분석: 기존 AI 결과 / segments / speakers 삭제 후 재생성 (한 트랜잭션)
        ai_repo.delete_for_episode(db, episode_id)
        segment_repo.delete_for_episode(db, episode_id)
        speaker_repo.delete_for_episode(db, episode_id)
        db.flush()

        sp_ids: dict[str, uuid.UUID] = {}
        for i, code in enumerate(merged.speaker_codes):
            sp = EpisodeSpeaker(episode_id=episode_id, speaker_code=code_for(i), color=color_for(i))
            db.add(sp)
            db.flush()
            sp_ids[code] = sp.id
        # 코드 재부여(사용되지 않은 번호가 빠질 수 있으므로) 후 매핑
        for seq, m in enumerate(merged.segments, start=1):
            db.add(
                TranscriptSegment(
                    episode_id=episode_id,
                    speaker_id=sp_ids[m.speaker],
                    seq=seq,
                    start_time=round(m.start, 3),
                    end_time=round(m.end, 3),
                    original_text=m.text,
                )
            )
        ep.ai_status = AiStatus.NONE
        ep.stt_model = "mock" if settings.stt_provider == "mock" else settings.OPENAI_STT_MODEL
        episode_repo.set_status(
            db, ep, EpisodeStatus.TRANSCRIBED, error_stage=None, error_message=None,
            progress_current=ep.progress_total,
        )
