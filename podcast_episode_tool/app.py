from __future__ import annotations

import io
import zipfile
from pathlib import Path

import streamlit as st

from pipeline.analyze import analyze_candidates, format_seconds, text_between
from pipeline.config import INDEX_PATH, load_settings
from pipeline.embed import init_db, upsert_approved_clip
from pipeline.media import cut_audio, ffprobe_duration
from pipeline.models import Candidate
from pipeline.storage import (
    clip_base_name,
    load_candidates,
    load_transcript,
    recording_dir,
    recording_id,
    save_candidates,
    save_transcript,
    save_upload,
    write_clip_artifacts,
)
from pipeline.transcribe import parse_timed_text, transcribe_audio


st.set_page_config(page_title="사주 팟캐스트 에피소드 추출", layout="wide")
settings = load_settings()
init_db()

st.title("사주 팟캐스트 에피소드 추출")
st.warning("전사, 후보 분석, 임베딩은 외부 OpenAI API로 데이터가 전송되며 비용이 발생할 수 있습니다. 버튼을 누를 때만 API를 호출합니다.")

audio_file = st.file_uploader("음성 파일", type=["mp3", "m4a", "wav", "mp4"], accept_multiple_files=False)
txt_file = st.file_uploader("시간 표시 녹취록(.txt, 선택)", type=["txt"], accept_multiple_files=False)

if not audio_file and not txt_file:
    st.info("음성 파일 또는 시간 표시 녹취록을 넣어 주세요.")
    st.stop()

seed_name = audio_file.name if audio_file else txt_file.name
seed_bytes = audio_file.getvalue() if audio_file else txt_file.getvalue()
rid = recording_id(seed_name, seed_bytes)
rdir = recording_dir(rid)

audio_path: Path | None = None
duration = None
if audio_file:
    audio_path = save_upload(rid, audio_file.name, audio_file.getvalue())
    duration = ffprobe_duration(audio_path)

st.subheader("녹음 상태")
cols = st.columns(4)
cols[0].metric("녹음 ID", rid)
cols[1].metric("파일명", seed_name)
cols[2].metric("길이", format_seconds(duration) if duration else "알 수 없음")
cols[3].metric("API 키", "설정됨" if settings.openai_api_key else "없음")

transcript = load_transcript(rid)
if transcript:
    st.success("저장된 전사 결과를 복원했습니다.")

if st.button("전사 준비/실행", type="primary"):
    try:
        if txt_file:
            transcript = parse_timed_text(txt_file.name, txt_file.getvalue().decode("utf-8-sig"))
        elif audio_path and settings.openai_api_key:
            transcript = transcribe_audio(audio_path, audio_file.name, settings.openai_api_key, settings.transcribe_model)
        else:
            st.error("음성만 입력한 경우 전사를 위해 OPENAI_API_KEY가 필요합니다.")
            st.stop()
        if duration and transcript.duration and transcript.duration > duration + 60:
            st.error("전사 타임코드가 원본 길이를 크게 벗어납니다.")
            st.stop()
        save_transcript(rid, transcript)
        st.success("전사를 저장했습니다.")
    except Exception as exc:
        st.error(f"전사 처리 실패: {exc}")

transcript = load_transcript(rid)
if not transcript:
    st.stop()

with st.expander("전사문 보기", expanded=False):
    st.text("\n".join(f"[{format_seconds(s.start)}] {s.text}" for s in transcript.segments))

candidates = load_candidates(rid)
if candidates:
    st.success("저장된 후보 상태를 복원했습니다.")

if st.button("후보 분석 실행"):
    try:
        candidates = analyze_candidates(transcript, settings.openai_api_key, settings.analysis_model)
        save_candidates(rid, candidates)
        st.success(f"후보 {len(candidates)}개를 저장했습니다.")
    except Exception as exc:
        st.error(f"후보 분석 실패: {exc}")

candidates = load_candidates(rid) or []
if not candidates:
    st.info("후보 분석을 실행해 주세요.")
    st.stop()

st.subheader("후보 검토")
updated: list[Candidate] = []
for idx, candidate in enumerate(candidates):
    with st.container(border=True):
        st.markdown(f"#### {idx + 1}. {candidate.title}")
        left, right = st.columns([2, 1])
        with left:
            title = st.text_input("제목", candidate.title, key=f"title_{candidate.id}")
            summary = st.text_area("에피소드 내용 요약", candidate.summary, height=140, key=f"summary_{candidate.id}")
            question = st.text_input("청취자 질문", candidate.listener_question, key=f"q_{candidate.id}")
            reason = st.text_area("추천 이유", candidate.reason, height=120, key=f"r_{candidate.id}")
            usage_type = st.selectbox("활용 유형", ["원본 클립", "새 녹음 소재", "짧은 클립"], index=["원본 클립", "새 녹음 소재", "짧은 클립"].index(candidate.usage_type) if candidate.usage_type in ["원본 클립", "새 녹음 소재", "짧은 클립"] else 0, key=f"u_{candidate.id}")
            review_notes = st.text_area("공개 전 확인할 표현", candidate.review_notes, key=f"n_{candidate.id}")
        with right:
            max_value = float(duration or transcript.duration or max(candidate.end, 1))
            start = st.number_input("시작(초)", min_value=0.0, max_value=max_value, value=float(candidate.start), step=1.0, key=f"s_{candidate.id}")
            end = st.number_input("끝(초)", min_value=0.0, max_value=max_value + 3600, value=float(candidate.end), step=1.0, key=f"e_{candidate.id}")
            status = st.radio("상태", ["hold", "approved"], format_func=lambda x: "승인" if x == "approved" else "보류", index=1 if candidate.status == "approved" else 0, horizontal=True, key=f"st_{candidate.id}")
        transcript_text = text_between(transcript, start, end)
        edited_transcript = st.text_area("구간 전사문", transcript_text or candidate.transcript, height=140, key=f"t_{candidate.id}")
        if audio_path:
            st.audio(str(audio_path), format=f"audio/{audio_path.suffix.lstrip('.')}")
            st.caption("브라우저 플레이어에서 위 시간대로 이동해 미리 들어 주세요.")
        else:
            st.caption(".txt만 입력되어 미리듣기와 음성 분할은 비활성화됩니다.")
        updated.append(Candidate(
            id=candidate.id,
            title=title,
            summary=summary,
            listener_question=question,
            reason=reason,
            start=start,
            end=end,
            transcript=edited_transcript,
            usage_type=usage_type,
            review_notes=review_notes,
            status=status,
        ))

if st.button("후보 수정 저장"):
    save_candidates(rid, updated)
    st.success("후보 상태를 저장했습니다.")

if st.button("승인한 후보 처리", type="primary"):
    save_candidates(rid, updated)
    results = []
    for candidate in updated:
        if candidate.status != "approved":
            continue
        if candidate.end <= candidate.start:
            results.append((candidate.title, False, "시간 범위가 올바르지 않습니다."))
            continue
        if duration and candidate.end > duration:
            results.append((candidate.title, False, "끝 시간이 원본 길이를 벗어납니다."))
            continue
        clip_audio = None
        if audio_path:
            clip_audio = rdir / "clips" / f"{clip_base_name(candidate)}.mp3"
            ok, message = cut_audio(audio_path, candidate.start, candidate.end, clip_audio)
            if not ok:
                results.append((candidate.title, False, message))
                continue
        write_clip_artifacts(rid, candidate, clip_audio)
        inserted = upsert_approved_clip(rid, candidate, clip_audio, settings.openai_api_key, settings.embedding_model)
        db_message = "DB에 새로 기록" if inserted else "기존 DB 행 재사용"
        results.append((candidate.title, True, db_message))
    if not results:
        st.warning("승인된 후보가 없습니다.")
    for title, ok, message in results:
        (st.success if ok else st.error)(f"{title}: {message}")

st.subheader("결과")
st.write(f"결과 폴더: `{rdir}`")
st.write(f"SQLite 인덱스: `{INDEX_PATH}`")

zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
    for path in (rdir / "clips").glob("*"):
        zf.write(path, path.relative_to(rdir))
if zip_buffer.getbuffer().nbytes > 22:
    st.download_button("결과 ZIP 내려받기", zip_buffer.getvalue(), file_name=f"{rid}_clips.zip")
