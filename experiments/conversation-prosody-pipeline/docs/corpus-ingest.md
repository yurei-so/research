# Local corpus ingestion experiments

This workflow is for local experiments over caller-managed corpora. Corpus audio,
transcripts, and generated bulk results are ignored under `import/`; none of them are
part of the Python package or intended for commit. Treat a corpus input directory as
read-only and direct any converted audio to a separate ignored directory.

The runner recursively pairs PCM WAV files with caller-provided transcript text. It
supports either a same-stem sidecar (`turn.wav` plus `turn.txt`) or a LibriSpeech chapter
manifest (`123-456.trans.txt` containing lines such as `123-456-0000 TRANSCRIPT`). The
text is always supplied by the caller. The workflow performs no speech-to-text,
emotion inference, speaker identification, voiceprinting, or biometric profiling.

Run both ingestion APIs on a small sample with:

```bash
scripts/run_corpus_ingest import/wav-corpus --limit 25
```

The default mode is `both`; `--mode file` and `--mode stream` select one path. In both
mode, duration, normalized RMS energy, and transcript-derived speech rate are compared
and should match. Stream chunk size can be changed with `--chunk-duration-ms`.

Outputs default to ignored workspace paths:

- `import/outputs/corpus_metadata.jsonl`
- `import/reports/corpus_summary.csv`

Use `--output-jsonl PATH` and `--summary-csv PATH` to choose other locations. Keep
large experiment outputs beneath ignored paths rather than adding them to Git.

The ingestion APIs accept PCM WAV, not FLAC. This repository intentionally adds no
conversion dependency and has no conversion helper. If a source corpus contains only
FLAC, convert it externally into a separate ignored PCM WAV tree while preserving its
relative layout and `*.trans.txt` manifests, then point the runner at that tree. A
FLAC-only run exits before writing outputs and prints this requirement.

Whole-file RMS currently walks every PCM sample in pure Python. Full-corpus runs can
therefore be substantially slower than small experiments; start with `--limit` and
increase it deliberately.
