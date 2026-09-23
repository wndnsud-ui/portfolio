from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pipeline.transcribe import transcribe_audio


class FakeTranscriptions:
    def __init__(self, result: object) -> None:
        self.result = result
        self.kwargs: dict = {}

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.result


class TranscriptionFormatTests(unittest.TestCase):
    def call_model(self, model: str, result: object):
        endpoint = FakeTranscriptions(result)

        class FakeOpenAI:
            def __init__(self, api_key: str) -> None:
                self.audio = SimpleNamespace(transcriptions=endpoint)

        fake_module = types.ModuleType("openai")
        fake_module.OpenAI = FakeOpenAI
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio:
            path = Path(audio.name)
        try:
            with patch.dict(sys.modules, {"openai": fake_module}):
                transcript = transcribe_audio(path, path.name, "test-key", model)
        finally:
            path.unlink(missing_ok=True)
        return endpoint.kwargs, transcript

    def test_whisper_requests_verbose_json_timestamps(self) -> None:
        result = SimpleNamespace(
            segments=[SimpleNamespace(start=0, end=4, text="hello")],
            text="hello",
        )
        kwargs, transcript = self.call_model("whisper-1", result)
        self.assertEqual(kwargs["response_format"], "verbose_json")
        self.assertEqual(kwargs["timestamp_granularities"], ["segment"])
        self.assertEqual(transcript.segments[0].end, 4)

    def test_gpt_transcribe_requests_json_only(self) -> None:
        result = SimpleNamespace(text="hello", duration=12)
        kwargs, transcript = self.call_model("gpt-4o-mini-transcribe", result)
        self.assertEqual(kwargs["response_format"], "json")
        self.assertNotIn("timestamp_granularities", kwargs)
        self.assertEqual(transcript.segments[0].end, 12)


if __name__ == "__main__":
    unittest.main()
