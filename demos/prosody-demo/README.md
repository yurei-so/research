# Prosody Demo

A deliberately small web demo for comparing conversational endpointing strategies:

- **Mode A — Silence / VAD:** conventional endpointing baseline.
- **Mode B — Measured prosody:** transcript plus real acoustic/prosodic turn cues.

Speculative response generation is intentionally out of scope because the supporting experiments
did not justify promoting it into a live assistant path.

## Current slice

The repository currently provides a loopback-only Python web server, a minimal browser chat UI
with A/B mode selection, server-side Ollama model discovery and chat, timing telemetry, and a
pinned dependency on Conversation Prosody Pipeline `0.3.1` at its immutable release commit.

Recorded microphone turns are decoded with FFmpeg, transcribed locally with faster-whisper, and
measured by Conversation Prosody Pipeline. Mode B supplies those measurements to the LLM while
Mode A withholds them. The browser automatically stops Mode A after 900 ms of measured silence.
Mode B may stop after 450 ms when recent RMS energy or estimated pitch is falling, and otherwise
uses a conservative 1,000 ms silence fallback. Manual stop remains available, and the UI reports
the endpoint reason and timing near the mode controls. An off-by-default auto-send toggle can
submit a successfully transcribed and measured turn immediately. Streaming output and TTS are
later slices.

The dashboard retains the latest completed turn from each mode and shows Mode B minus Mode A for
endpoint wait, transcription-request pipeline, Ollama round trip, and an estimated post-speech
total. It also
shows the Ollama round-trip difference from the immediately previous turn. These are observational
comparisons unless the same recording and generation settings are replayed through both modes.

The Mode B detector is deliberately a small measured-acoustics heuristic, not a trained turn-state
model. Its pitch estimate covers roughly 70–400 Hz and its finality cue is an observable falling
energy or pitch trend. This makes the first comparison inspectable while we collect evidence for a
better policy.

## Run

Requirements: Python 3.11+, Git, FFmpeg, a running Ollama server, and at least one installed model.

```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[speech]'
.venv/bin/prosody-demo
```

Open <http://127.0.0.1:8765>. Set `OLLAMA_BASE_URL` to use another operator-controlled Ollama
endpoint. The browser cannot choose an arbitrary backend URL.

The default local STT model is `small.en`. Override it with `WHISPER_MODEL`; faster-whisper may
download the selected model on first use. Raw recordings and converted WAV files live only in a
per-request temporary directory and are deleted after transcription and measurement.

## Test

```bash
.venv/bin/python -m unittest discover -s tests
node --test tests/test_endpointing.js
```

## Package provenance

Conversation Prosody Pipeline package version `0.3.1` corresponds to commit `b346620`. The
missing local annotated tag was restored as `v0.3.1`; publishing that tag is separate.
