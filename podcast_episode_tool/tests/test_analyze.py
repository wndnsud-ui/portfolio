import unittest

from pipeline.analyze import (
    ensure_meaningful_transcript,
    has_excessive_silence,
    normalize_candidate_times,
    speech_bounds,
)
from pipeline.models import Candidate, Segment, Transcript


class AnalysisValidationTests(unittest.TestCase):
    def test_rejects_speaker_labels_without_spoken_content(self):
        transcript = Transcript(
            source_name="bad.txt",
            duration=20,
            segments=[Segment(start=i, end=i + 1, text=f"참석자 {(i % 3) + 1}") for i in range(10)],
        )
        with self.assertRaisesRegex(ValueError, "실제 발화"):
            ensure_meaningful_transcript(transcript)

    def test_uses_referenced_timecodes_instead_of_incorrect_seconds(self):
        transcript = Transcript(
            source_name="episode.txt",
            duration=320,
            segments=[
                Segment(start=271, end=273, text="첫 번째 실제 발화입니다."),
                Segment(start=273, end=275, text="두 번째 실제 발화입니다."),
                Segment(start=304, end=314, text="마지막 실제 발화입니다."),
            ],
        )
        candidate = Candidate(
            title="후보",
            listener_question="질문",
            reason="이유",
            start=40,
            end=56,
            transcript="[04:31] 첫 번째 실제 발화입니다.\n[05:04] 마지막 실제 발화입니다.",
            usage_type="원본 클립",
        )

        self.assertEqual(normalize_candidate_times(candidate, transcript), (271, 314))

    def test_trims_edges_and_rejects_long_internal_silence(self):
        transcript = Transcript(
            source_name="episode.mp3",
            duration=60,
            segments=[
                Segment(start=5, end=10, text="첫 발화입니다."),
                Segment(start=25, end=30, text="긴 무음 뒤 발화입니다."),
            ],
        )
        self.assertEqual(speech_bounds(transcript, 0, 40), (5, 30))
        self.assertTrue(has_excessive_silence(transcript, 5, 30))


if __name__ == "__main__":
    unittest.main()
