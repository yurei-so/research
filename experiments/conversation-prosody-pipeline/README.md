# Conversation Prosody Pipeline

[![License: MIT](https://img.shields.io/github/license/yurei-dll/conversation-prosody-pipeline)](LICENSE) [![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/) [![Package version](https://img.shields.io/badge/version-0.3.0-blue)](https://github.com/yurei-dll/conversation-prosody-pipeline) [![Package](https://github.com/yurei-dll/conversation-prosody-pipeline/actions/workflows/package.yml/badge.svg)](https://github.com/yurei-dll/conversation-prosody-pipeline/actions/workflows/package.yml)

> A modular middleware pipeline that enriches spoken conversations with conversational metadata before they reach a language model.

## Why?

Modern voice assistants typically reduce speech to plain text before sending it to a language model.

Unfortunately, conversations are much richer than text alone.

Consider these two utterances:

> "Yeah... I'm fine."

The transcript is identical.

The conversation is not.

One speaker may answer instantly with a laugh.

Another may pause for several seconds, speak quietly, and trail off at the end of the sentence.

Humans naturally use these vocal cues to understand one another. Most current LLM pipelines discard them entirely.

This project exists to preserve that information.

---

## Philosophy

Conversation Prosody Pipeline **does not attempt to determine emotions.**

Instead, it extracts measurable conversational features and exposes them as structured metadata.

Examples include:

* Speech rate
* Pause duration
* Speaking energy
* Pitch variability
* Turn-taking statistics
* Response latency
* Hesitation frequency
* Conversation pacing

Rather than outputting:

```json
{
  "emotion": "sad"
}
```

the pipeline prefers outputs like:

```json
{
  "speech_rate_delta": -18.3,
  "pause_delta": 0.42,
  "energy_delta": -0.27,
  "pitch_variability_delta": -0.38
}
```

These are observations, not conclusions.

The downstream language model remains responsible for reasoning about what those observations might mean.

---

## Goals

* Preserve conversational information that transcripts lose.
* Remain model-agnostic.
* Avoid identity recognition or biometric tracking.
* Operate as middleware rather than a replacement for existing LLMs.
* Keep outputs interpretable and measurable.

---

## Architecture

```text
Microphone
      │
      ▼
Speech Recognition
      │
      ▼
Prosody Extraction
      │
      ▼
Conversation State
      │
      ▼
Structured Metadata (JSON)
      │
      ▼
Language Model
      │
      ▼
Response
```

The language model receives both the transcript and conversational metadata.

Example:

```json
{
  "schema_version": "1.0",
  "transcript": "Yeah, that's fine.",
  "timing": {
    "start_ms": 840,
    "end_ms": 2380,
    "duration_ms": 1540
  },
  "features": {
    "speech_rate_wpm": 92,
    "pause_before_ms": 310,
    "energy_rms": 0.18,
    "interruption_count": 0
  },
  "deltas": {
    "absolute": {
      "speech_rate_wpm": -24,
      "pause_before_ms": 180
    },
    "relative": {
      "speech_rate_wpm": -0.21,
      "pause_before_ms": 1.38
    }
  },
  "baseline_sample_count": 4
}
```

The pipeline intentionally avoids prescribing an interpretation.

---

## Groundwork

This repository now includes a small Python core for experimenting with the metadata
shape described above:

```text
src/conversation_prosody_pipeline/
  baseline.py   Conversation-local running baselines
  audio_file.py Dependency-free WAV file ingestion
  audio_stream.py Experimental WAV-backed stream ingestion
  extractors.py Extractor interfaces and dependency-free mock extractor
  pipeline.py   Turn-by-turn metadata builder
  types.py      Typed turn, feature, and metadata objects
```

The current metadata schema includes a serialized `schema_version` and optional
per-turn `timing` in milliseconds. The Python package has no runtime dependencies;
audio extraction libraries are intentionally not part of this groundwork layer yet.

Run the minimal example:

```bash
scripts/venv run python examples/minimal_turn.py
```

Run the mock extractor example:

```bash
scripts/venv run python examples/mock_extractor.py
```

Run the simulated streaming WAV example:

```bash
scripts/venv run python examples/ingest_wav_stream.py
```

Run tests:

```bash
scripts/venv run python -m unittest discover -s tests
```

Manage a local virtualenv:

```bash
scripts/venv install
source .venv/bin/activate
```

VS Code users can run the same workflow through `Tasks: Run Task`:

```text
venv: create
venv: install
venv: recreate
venv: remove
example: minimal turn
test: unittest
```

See also:

* [Development guide](DEVELOPMENT.md)
* [Architecture](docs/architecture.md)
* [Licensing and dependency boundaries](docs/licensing.md)
* [Data and artifact policy](docs/data-policy.md)
* [Prior art and research context](docs/prior-art.md)
* [Simulated audio stream ingest](docs/audio-stream-ingest.md)
* [Real-time application integration](docs/realtime-application.md)
* [Experiment labnotes](docs/labnotes/README.md)
* [Metadata schema](docs/metadata-schema.md)
* [Roadmap](docs/roadmap.md)

---

## Privacy

This project intentionally avoids persistent speaker identification.

Conversation Prosody Pipeline analyzes **how speech changes during the current conversation**, not **who is speaking**.

No emotion labels, speaker identity, persistent voiceprints, biometric databases,
or long-term speaker profiles are required.

The goal is to improve conversational context while minimizing privacy concerns.

---

## Design Principles

* Modular over monolithic.
* Observations over assumptions.
* Middleware over end-to-end replacement.
* Privacy by design.
* Model agnostic.

---

## Potential Applications

* Voice assistants
* Accessibility software
* Educational tutors
* Companion AIs
* Customer support
* Research
* Robotics
* Interactive storytelling

Any system that benefits from understanding conversational dynamics without relying solely on transcripts.

---

## Status

🚧 Early concept.

This repository currently focuses on architecture, experimentation, and validating whether structured conversational metadata can improve downstream language model interactions.

Contributions, experiments, and alternative approaches are welcome.
