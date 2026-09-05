import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from prosody_demo.speech import SpeechError, SpeechProcessor


def write_test_wav(path: Path) -> None:
    samples = (b"\x00\x00\x10\x00\xf0\xff" * 1600)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(samples)


class SpeechProcessorTests(unittest.TestCase):
    def test_rejects_unknown_recording_type(self):
        with self.assertRaisesRegex(SpeechError, "Unsupported recording type"):
            SpeechProcessor._suffix_for("video/webm")

    def test_processes_turn_and_keeps_session_baseline(self):
        processor = SpeechProcessor()

        def fake_convert(_source, target):
            write_test_wav(target)

        with patch.object(processor, "_convert_to_wav", side_effect=fake_convert), patch.object(
            processor, "_transcribe", return_value=("hello world", "en", 0.99)
        ):
            first = processor.process(b"audio", "audio/webm", "session-1")
            second = processor.process(b"audio", "audio/webm", "session-1")
        self.assertEqual(first["prosody"]["baseline_sample_count"], 0)
        self.assertEqual(second["prosody"]["baseline_sample_count"], 1)
        self.assertEqual(second["transcript"], "hello world")


if __name__ == "__main__":
    unittest.main()
