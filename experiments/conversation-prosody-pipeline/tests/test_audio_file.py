import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from conversation_prosody_pipeline import ProsodyPipeline, ingest_wav_file, read_wav_info


class AudioFileIngestTests(unittest.TestCase):
    def test_read_wav_info_reports_standard_library_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = Path(temp_dir) / "turn.wav"
            self._write_pattern_wav(wav_path)

            info = read_wav_info(wav_path)

        self.assertEqual(info.sample_rate, 8000)
        self.assertEqual(info.frame_count, 8000)
        self.assertEqual(info.sample_width, 2)
        self.assertEqual(info.channel_count, 1)
        self.assertEqual(info.duration_ms, 1000.0)

    def test_ingest_wav_file_builds_turn_timing_and_basic_features(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = Path(temp_dir) / "turn.wav"
            self._write_pattern_wav(wav_path)

            turn, features = ingest_wav_file(wav_path, "one two three four")

        self.assertEqual(turn.transcript, "one two three four")
        self.assertEqual(turn.timing.duration_ms, 1000.0)
        self.assertEqual(turn.metadata["source"], "wav_file")
        self.assertEqual(turn.metadata["wav"]["sample_rate"], 8000)
        self.assertEqual(features.duration_ms, 1000.0)
        self.assertEqual(features.speech_rate_wpm, 240.0)
        self.assertTrue(math.isclose(features.energy_rms, math.sqrt(0.125), rel_tol=1e-12))

    def test_ingested_turn_can_flow_through_prosody_pipeline_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = Path(temp_dir) / "turn.wav"
            self._write_pattern_wav(wav_path)
            turn, features = ingest_wav_file(wav_path, "pipeline shaped transcript")

            metadata = ProsodyPipeline().process_turn(
                transcript=turn.transcript,
                features=features,
                timing=turn.timing,
            )

        serialized = metadata.to_dict()
        self.assertEqual(serialized["transcript"], "pipeline shaped transcript")
        self.assertEqual(serialized["features"]["duration_ms"], 1000.0)
        self.assertIn("energy_rms", serialized["features"])
        self.assertEqual(serialized["timing"]["duration_ms"], 1000.0)

    @staticmethod
    def _write_pattern_wav(path: Path) -> None:
        samples = [0, 16384, -16384, 0] * 2000
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(8000)
            for sample in samples:
                wav_file.writeframesraw(struct.pack("<h", sample))
