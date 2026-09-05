import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from conversation_prosody_pipeline import (
    RawTurn,
    TurnFeatures,
    ingest_wav_file,
    ingest_wav_stream,
    iter_wav_chunks,
)


class AudioStreamIngestTests(unittest.TestCase):
    def test_iter_wav_chunks_yields_ordered_chunks_and_final_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = Path(temp_dir) / "turn.wav"
            self._write_pattern_wav(wav_path, frame_count=1000)

            chunks = list(iter_wav_chunks(wav_path, chunk_duration_ms=100.0))

        self.assertEqual(len(chunks), 5)
        self.assertTrue(chunks[-1].is_final)
        self.assertFalse(any(chunk.is_final for chunk in chunks[:-1]))
        self.assertEqual(chunks[0].start_ms, 0.0)
        self.assertEqual(chunks[1].start_ms, 100.0)
        self.assertEqual(chunks[0].sample_rate, 2000)
        self.assertEqual(chunks[0].sample_width, 2)
        self.assertEqual(chunks[0].channel_count, 1)

    def test_total_chunk_duration_matches_wav_duration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = Path(temp_dir) / "turn.wav"
            self._write_pattern_wav(wav_path, frame_count=1000)

            chunks = list(iter_wav_chunks(wav_path, chunk_duration_ms=128.0))

        total_duration_ms = sum(chunk.duration_ms for chunk in chunks)
        self.assertTrue(math.isclose(total_duration_ms, 500.0, abs_tol=0.001))

    def test_streaming_ingest_returns_turn_and_features(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = Path(temp_dir) / "turn.wav"
            self._write_pattern_wav(wav_path, frame_count=2000)

            turn, features = ingest_wav_stream(wav_path, "one two three", chunk_duration_ms=75.0)

        self.assertIsInstance(turn, RawTurn)
        self.assertIsInstance(features, TurnFeatures)
        self.assertEqual(turn.transcript, "one two three")
        self.assertEqual(turn.metadata["source"], "wav_stream")
        self.assertTrue(turn.metadata["is_complete"])
        self.assertTrue(math.isclose(features.duration_ms, 1000.0, abs_tol=0.001))
        self.assertTrue(math.isclose(features.speech_rate_wpm, 180.0, abs_tol=0.001))

    def test_streaming_rms_is_close_to_file_ingest_rms(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = Path(temp_dir) / "turn.wav"
            self._write_pattern_wav(wav_path, frame_count=2250)

            _, file_features = ingest_wav_file(wav_path, "same transcript")
            _, stream_features = ingest_wav_stream(
                wav_path,
                "same transcript",
                chunk_duration_ms=90.0,
            )

        self.assertTrue(
            math.isclose(stream_features.duration_ms, file_features.duration_ms, abs_tol=0.001)
        )
        self.assertTrue(
            math.isclose(stream_features.energy_rms, file_features.energy_rms, rel_tol=1e-12)
        )

    @staticmethod
    def _write_pattern_wav(path: Path, frame_count: int) -> None:
        samples = [0, 8000, -12000, 16000]
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(2000)
            for index in range(frame_count):
                wav_file.writeframesraw(struct.pack("<h", samples[index % len(samples)]))
