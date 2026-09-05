# Metadata Schema

Conversation Prosody Pipeline emits observations that can travel beside transcript text.
The schema is deliberately small while the project is still validating which features
are most useful downstream.

## Turn Metadata

```json
{
  "schema_version": "1.0",
  "transcript": "Yeah... I'm fine.",
  "timing": {
    "start_ms": 1200,
    "end_ms": 3420,
    "duration_ms": 2220
  },
  "features": {
    "duration_ms": 2220,
    "speech_rate_wpm": 98,
    "pause_before_ms": 860,
    "energy_rms": 0.21,
    "pitch_variability_hz": 24,
    "hesitation_count": 1
  },
  "deltas": {
    "absolute": {
      "speech_rate_wpm": -54,
      "pause_before_ms": 740
    },
    "relative": {
      "speech_rate_wpm": -0.36,
      "pause_before_ms": 6.17
    }
  },
  "baseline_sample_count": 1
}
```

## Field Notes

- `schema_version` identifies the metadata contract used by the serialized turn.
- `timing` is optional turn timing in milliseconds when an upstream system already
  has reliable boundaries for the transcript turn.
- `features` are direct measurements for the current turn, such as duration,
  transcript-derived speech rate, and RMS energy.
- `deltas.absolute` compares the turn against the conversation-local baseline in the
  feature's native unit.
- `deltas.relative` compares the turn against the baseline as a fractional change.
- `baseline_sample_count` reports how much prior conversation informed the deltas.

The pipeline should not emit emotion labels, speaker identity, persistent voiceprints,
or any other biometric tracking metadata.
