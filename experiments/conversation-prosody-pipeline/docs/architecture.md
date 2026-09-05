# Architecture

Conversation Prosody Pipeline is middleware. It accepts pipeline-native turn
objects and measurable observations, keeps conversation-local baseline state, and
emits structured metadata for downstream language models.

```text
Audio/STT
    |
    v
Adapter / Extractor
    |
    v
Conversation Prosody Pipeline
    |
    v
Structured Metadata
    |
    v
LLM
```

## Layers

- `Audio/STT` captures speech and may produce transcripts, timestamps, word-level
  metadata, or engine-specific confidence values.
- `Adapter / Extractor` converts external formats into pipeline-native types such
  as `RawTurn`, `TurnFeatures`, and `TurnTiming`.
- `Conversation Prosody Pipeline` compares measurable turn features against the
  current conversation baseline and builds `TurnMetadata`.
- `Structured Metadata` serializes observations and deltas without adding emotion
  labels, speaker identity, persistent voiceprints, or biometric tracking data.
- `LLM` receives the transcript and metadata, then decides how to use those
  observations in context.

Adapters are the boundary between speech engines and this package. A Whisper,
Deepgram, Vosk, or custom integration can map its own output into `RawTurn` and
extract `TurnFeatures`, but the pipeline itself should never know which engine
produced the data.

The core package intentionally has no external audio-processing dependencies. It
does include a minimal standard-library WAV ingest helper for local validation:
the caller provides the transcript, no STT is performed, and the helper computes
only duration, RMS energy, and transcript-derived speech rate. Future feature
extractors can live beside the core or in integration packages while the
middleware contract remains small, testable, and engine-agnostic.

See [Audio file ingest](audio-file-ingest.md) for the WAV-only milestone path.
