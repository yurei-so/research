from __future__ import annotations

import csv
import json
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from conversation_prosody_pipeline.corpus_ingest import (
    discover_pairs,
    ingest_pair,
    write_jsonl,
    write_summary_csv,
)


class CorpusIngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_discovers_sidecars_and_librispeech_manifests(self) -> None:
        self._write_wav(self.root / "sidecar.wav")
        (self.root / "sidecar.txt").write_text("caller provided sidecar\n", encoding="utf-8")
        chapter = self.root / "123" / "456"
        self._write_wav(chapter / "123-456-0000.wav")
        (chapter / "123-456.trans.txt").write_text(
            "123-456-0000 CALLER PROVIDED MANIFEST\n", encoding="utf-8"
        )

        discovery = discover_pairs(self.root)

        self.assertEqual(discovery.wav_count, 2)
        self.assertEqual(len(discovery.pairs), 2)
        self.assertEqual(
            {pair.transcript for pair in discovery.pairs},
            {"caller provided sidecar", "CALLER PROVIDED MANIFEST"},
        )

    def test_reports_wavs_with_missing_transcripts(self) -> None:
        wav_path = self.root / "missing.wav"
        self._write_wav(wav_path)

        discovery = discover_pairs(self.root)

        self.assertEqual(discovery.pairs, [])
        self.assertEqual(discovery.missing_transcripts, [wav_path])

    def test_writes_one_json_object_per_line(self) -> None:
        records = [self._record("first"), self._record("second")]
        output_path = self.root / "nested" / "metadata.jsonl"

        write_jsonl(output_path, records)

        written = [json.loads(line) for line in output_path.read_text().splitlines()]
        self.assertEqual(written, records)

    def test_writes_csv_summary_for_each_requested_mode(self) -> None:
        record = self._record("sample")
        output_path = self.root / "reports" / "summary.csv"

        write_summary_csv(output_path, [record])

        with output_path.open(encoding="utf-8", newline="") as source:
            rows = list(csv.DictReader(source))
        self.assertEqual([row["mode"] for row in rows], ["file", "stream"])
        self.assertEqual(rows[0]["audio_path"], "sample.wav")
        self.assertEqual(rows[0]["features_match"], "True")

    def test_file_and_stream_features_match_for_generated_wav(self) -> None:
        wav_path = self.root / "turn.wav"
        transcript_path = self.root / "turn.txt"
        self._write_wav(wav_path, frame_count=2_675)
        transcript_path.write_text("one two three four", encoding="utf-8")
        pair = discover_pairs(self.root).pairs[0]

        record = ingest_pair(pair, mode="both", chunk_duration_ms=73.0)

        self.assertTrue(record["features_match"])
        for feature_name in ("duration_ms", "energy_rms", "speech_rate_wpm"):
            comparison = record["comparison"][feature_name]
            self.assertTrue(comparison["match"])
            self.assertTrue(
                math.isclose(comparison["file"], comparison["stream"], abs_tol=1e-6)
            )

    @staticmethod
    def _write_wav(path: Path, frame_count: int = 2_000) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        samples = [0, 8_000, -12_000, 16_000]
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(2_000)
            for index in range(frame_count):
                wav_file.writeframesraw(struct.pack("<h", samples[index % len(samples)]))

    @staticmethod
    def _record(name: str) -> dict[str, object]:
        features = {"duration_ms": 1_000.0, "energy_rms": 0.25, "speech_rate_wpm": 120.0}
        return {
            "audio_path": f"{name}.wav",
            "transcript_path": f"{name}.txt",
            "transcript": name,
            "modes": {
                "file": {"source": "wav_file", "features": features},
                "stream": {
                    "source": "wav_stream",
                    "chunk_count": 10,
                    "chunk_duration_ms": 100.0,
                    "features": features,
                },
            },
            "features_match": True,
        }


if __name__ == "__main__":
    unittest.main()
