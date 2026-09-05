# Simulated Audio Stream Ingest

The experimental streaming path in `audio_stream.py` uses WAV files as
deterministic simulated audio streams. It exists to validate the stream-processing
architecture before any live capture adapter is introduced.

This is not live microphone support. The module does not open devices, capture
audio, call speech-to-text services, infer emotion, identify speakers, or store
voiceprints. It uses only the Python standard library and reads local PCM WAV
data with `wave`.

## Shape

- `AudioChunk` carries raw PCM bytes, audio format fields, chunk timing, and an
  `is_final` marker.
- `iter_wav_chunks()` reads a WAV file incrementally and yields ordered chunks
  without loading the full file at once.
- `StreamingFeatureAccumulator` accepts chunks one at a time and accumulates
  minimal measurable features: duration and RMS energy.
- `ingest_wav_stream()` runs the simulated stream and returns the same
  pipeline-native `RawTurn` and `TurnFeatures` shape used elsewhere.

Transcripts remain caller-provided. Passing a transcript at finalization time
allows the accumulator to compute `speech_rate_wpm`; no STT is performed.

This experiment establishes that features can be accumulated incrementally without
requiring the complete audio in memory. The planned real-time API will replace its
WAV-oriented chunk lifecycle with a validated, transport-neutral turn interface
while keeping deterministic WAV input as a test and example source. See
[Real-time application integration](realtime-application.md) for the external
application shape and [Roadmap](roadmap.md) for the implementation milestone.
