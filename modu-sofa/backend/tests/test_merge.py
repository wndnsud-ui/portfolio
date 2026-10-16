from app.services.transcription_service import ChunkResult, RawSegment, merge_chunks
from app.utils.ffmpeg_utils import chunk_plan


def test_chunk_plan_matches_spec():
    plan = chunk_plan(2700, 1200, 15)
    assert [round(o) for o, _ in plan] == [0, 1185, 2370]
    assert plan[-1][0] + plan[-1][1] == 2700
    assert chunk_plan(600, 1200, 15) == [(0.0, 600)]


def _seg(st, en, sp, text):
    return RawSegment(start=st, end=en, speaker=sp, text=text)


def test_offset_overlap_and_speaker_unification():
    # 청크 0: 0~1200, 청크 1: 1185~2385 (겹침 1185~1200, 경계 1192.5)
    c0 = ChunkResult(
        0, 0, 1200,
        [
            _seg(0, 5, "A", "첫 문장"),
            _seg(6, 10, "B", "둘째 문장"),
            _seg(1186, 1191, "B", "겹침 앞쪽"),  # 경계 이전 → 청크 0에서 채택
            _seg(1193, 1199, "A", "겹침 뒤쪽 (청크0 버전)"),  # 경계 이후 → 버림
        ],
    )
    # 청크 1에서는 라벨이 뒤바뀌어 나온다: 청크0의 B = 청크1의 A
    c1 = ChunkResult(
        1, 1185, 1200,
        [
            _seg(1, 6, "A", "겹침 앞쪽 (청크1 버전)"),  # 1186~1191 → 경계 이전 → 버림
            _seg(8, 14, "B", "겹침 뒤쪽"),  # 1193~1199 → 채택
            _seg(20, 25, "C", "새 화자"),
        ],
    )
    out = merge_chunks([c1, c0], duration=2385)
    texts = [s.text for s in out.segments]
    assert texts == ["첫 문장", "둘째 문장", "겹침 앞쪽", "겹침 뒤쪽", "새 화자"]
    starts = [s.start for s in out.segments]
    assert starts == sorted(starts)
    assert out.segments[3].start == 1193  # offset 보정
    sp = {s.text: s.speaker for s in out.segments}
    assert sp["첫 문장"] == "SPEAKER_01"
    assert sp["둘째 문장"] == "SPEAKER_02"
    # 청크1의 B는 겹침 구간에서 청크0의 A(SPEAKER_01)와 겹친다
    assert sp["겹침 뒤쪽"] == "SPEAKER_01"
    assert sp["새 화자"] == "SPEAKER_03"
    assert out.speaker_codes == ["SPEAKER_01", "SPEAKER_02", "SPEAKER_03"]


def test_no_duplicates_or_gaps_across_boundaries_with_mock_timeline():
    from app.services import openai_client
    from app.services.transcription_service import parse_diarized

    duration = 2700.0
    plan = chunk_plan(duration, 1200, 15)
    chunks = [
        ChunkResult(i, o, ln, parse_diarized(openai_client._mock_transcribe(o, ln)))
        for i, (o, ln) in enumerate(plan)
    ]
    out = merge_chunks(chunks, duration)
    timeline = [t for t in openai_client._mock_timeline(duration + 30) if t[0] < duration]
    assert len(out.segments) == len(timeline)
    for got, (st, _en, _sp, text) in zip(out.segments, timeline):
        assert abs(got.start - st) < 0.02
        assert got.text == text
    assert all(s.end <= duration for s in out.segments)
    # 겹침 구간에 나오지 않은 화자는 새 화자로 분리될 수 있다(병합 화면으로 보정).
    # 대신 서로 다른 사람이 한 화자로 섞이면 안 된다.
    assert len(out.speaker_codes) >= 3
    truth_by_code: dict[str, set[int]] = {}
    for got, t in zip(out.segments, timeline):
        truth_by_code.setdefault(got.speaker, set()).add(t[2])
    assert all(len(v) == 1 for v in truth_by_code.values())
