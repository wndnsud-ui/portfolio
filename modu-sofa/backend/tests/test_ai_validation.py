import uuid
from types import SimpleNamespace

from app.services import chapter_service, highlight_service
from app.services.ai_input import AiSegment, fmt_ts, line


def _items(n=40, step=10.0):
    out = []
    for i in range(n):
        seg = SimpleNamespace(id=uuid.uuid4(), start_time=i * step, end_time=i * step + step - 1, seq=i + 1)
        out.append(AiSegment(ref=i + 1, segment=seg, speaker="혜영", text=f"문장 {i + 1}"))
    return out


def test_line_format():
    a = _items(1)[0]
    assert line(a) == "[seg=1][00:00.0][혜영] 문장 1"
    assert fmt_ts(72.44) == "01:12.4"


def test_chapters_drop_unknown_ids_sort_and_force_first():
    items = _items()
    raw = [
        {"start_segment_id": 20, "title": "중간", "description": ""},
        {"start_segment_id": 999, "title": "없는 ID", "description": ""},
        {"start_segment_id": 5, "title": "앞", "description": ""},
        {"start_segment_id": 30, "title": "끝", "description": ""},
    ]
    out = chapter_service.validate(raw, items, 3, 12)
    assert out is not None
    assert [c.seg.ref for c in out] == [1, 20, 30]  # 첫 챕터는 첫 Segment
    assert [c.title for c in out] == ["앞", "중간", "끝"]


def test_chapters_below_minimum_fail():
    items = _items()
    raw = [{"start_segment_id": 999, "title": "x", "description": ""}]
    assert chapter_service.validate(raw, items, 3, 12) is None


def test_chapter_target_range():
    assert chapter_service.target_range(42 * 60, 500) == (5, 10)
    assert chapter_service.target_range(5 * 60, 500) == (3, 3)
    assert chapter_service.target_range(90 * 60, 500) == (9, 12)


def test_highlights_quote_from_real_text_and_length_rules():
    items = _items()
    raw = [
        {"start_segment_id": 3, "end_segment_id": 5, "title": "좋은 구간"},  # 20~49s → 29초
        {"start_segment_id": 10, "end_segment_id": 9, "title": "역순"},
        {"start_segment_id": 12, "end_segment_id": 12, "title": "너무 짧음"},  # 9초
        {"start_segment_id": 15, "end_segment_id": 30, "title": "너무 김"},  # 159초
        {"start_segment_id": 20, "end_segment_id": 22, "title": "둘째"},
        {"start_segment_id": 4, "end_segment_id": 6, "title": "겹침"},
    ]
    out = highlight_service.validate(raw, items, 1)
    assert out is not None
    assert [h.title for h in out] == ["좋은 구간", "둘째"]
    assert out[0].text == "문장 3 문장 4 문장 5"
    assert highlight_service.validate(raw, items, 3) is None


def test_analysis_settings_reload_without_restart(monkeypatch):
    from app.core.config import reload_analysis_settings, settings

    monkeypatch.setenv("OPENAI_LLM_MODEL", "test-model-x")
    reload_analysis_settings()
    assert settings.OPENAI_LLM_MODEL == "test-model-x"
    monkeypatch.delenv("OPENAI_LLM_MODEL")
