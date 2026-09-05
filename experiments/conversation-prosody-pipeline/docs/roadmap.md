# Roadmap

## Current Groundwork

- Define observable per-turn feature objects.
- Track conversation-local baselines.
- Emit versioned structured metadata beside transcript text.
- Ingest PCM WAV files through whole-file and deterministic chunked paths.
- Validate equivalent aggregate features across file and simulated-stream ingest.
- Keep the core implementation dependency-free and easy to test.

## Real-Time Turn Ingestion

The next milestone is a transport-neutral API that external applications can feed
with PCM audio as it arrives. Metadata will initially be emitted only after the
audio turn and its caller-provided transcript are complete.

- Define an explicit PCM format containing encoding, sample rate, and channel
  count.
- Add a streaming-turn lifecycle with start, audio push, and one-time finalization
  operations.
- Derive duration from received PCM frames rather than caller-provided chunk
  durations.
- Detect incomplete frames, missing or duplicated chunks, reordered chunks, and
  format changes.
- Keep audio completion separate from transcript availability.
- Finalize streaming measurements through the existing `ProsodyPipeline` and
  update conversation baselines only once per completed turn.
- Make conversation-session lifetime and reset behavior explicit so independent
  conversations cannot share baseline state.
- Refactor deterministic WAV streaming to exercise the same public lifecycle used
  by live external producers.
- Add tests for variable chunk sizes, invalid ordering, lifecycle errors,
  multi-turn baselines, and session isolation.
- Provide a dependency-free example that imitates an external application feeding
  audio and a final transcript into CPP.

Turn boundaries will initially remain the responsibility of the external
application, STT provider, or voice-activity-detection adapter. See
[Real-time application integration](realtime-application.md) for the intended
application shape and contract boundaries.

## Downstream Evaluation

- Compare responses from the same off-the-shelf LLM with transcript-only and
  transcript-plus-metadata inputs.
- Hold source audio, transcript, conversation context, prompt, model, sampling
  settings, and CPP baseline state constant between conditions.
- Evaluate cases where delivery should inform a response and control cases where
  it should not.
- Measure whether metadata improves useful conversational sensitivity without
  encouraging unsupported emotion, identity, health, personality, or intent
  claims.
- Use ablations and counterfactual feature changes to test whether the downstream
  model actually responds to individual observations.

## Later Experiments

- Add adapters for real speech-recognition timing data.
- Explore rolling-window baselines for long conversations.
- Add privacy checks for persistence boundaries.
- Evaluate additional acoustic and interactional features.
- Add an optional reference WebSocket, gRPC, or application-SDK adapter after the
  transport-neutral stream contract is stable.
- Explore explicitly marked provisional metadata emitted during a turn without
  allowing provisional observations to contaminate finalized baselines.
- Evaluate causal windows, backchannels, interruptions, and overlapping speech.
