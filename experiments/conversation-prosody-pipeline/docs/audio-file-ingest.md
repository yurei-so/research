# Audio File Ingest

This package includes a minimal local WAV ingestion path for validating the
pipeline shape before adding real speech adapters.

`conversation_prosody_pipeline.audio_file` uses only the Python standard library
`wave` module. It supports WAV files only, assumes the transcript is provided by
the caller, and performs no speech-to-text.

The helper reads basic WAV metadata:

- sample rate
- frame count
- duration in milliseconds
- sample width
- channel count

It computes only basic observable features:

- `duration_ms`
- `energy_rms` from PCM samples when possible
- `speech_rate_wpm` from caller-provided transcript word count and WAV duration

It does not infer emotion, identify speakers, persist voiceprints, or create
biometric profiles.

```python
from conversation_prosody_pipeline import ProsodyPipeline, ingest_wav_file

turn, features = ingest_wav_file("turn.wav", "Caller provided transcript.")
metadata = ProsodyPipeline().process_turn(
    transcript=turn.transcript,
    features=features,
    timing=turn.timing,
)

print(metadata.to_dict())
```

Run the example with your own WAV file and transcript:

```bash
scripts/venv run python examples/ingest_wav_file.py path/to/turn.wav "Caller transcript"
```

Or run it without arguments to generate a temporary one-second WAV file:

```bash
scripts/venv run python examples/ingest_wav_file.py
```
