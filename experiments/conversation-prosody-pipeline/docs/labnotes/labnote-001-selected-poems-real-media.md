# Lab note: Selected Poems real-media ingest (v0.1.0)

**Run date:** 2026-06-27  
**Package:** `conversation-prosody-pipeline` 0.1.0  
**Metadata schema:** 1.0  
**Status:** Successful

## Question

Can the packaged file and simulated-stream ingestion paths produce consistent
prosodic metadata from real spoken audio when transcription remains an external step?

## Setup

The experiment ran outside the source tree in the disposable workspace
`~/Downloads/workspace`. It used four of seven recordings from LibriVox's public-domain
*Selected Poems of Sidney Lanier* archive:

- Source: <https://archive.org/details/selectedpoems_lulahragsdale_2606_librivox>
- Input archive: `selectedpoems_lulahragsdale_2606_librivox.zip`
- Input archive SHA-256: `69a4f10a0f6bef4d1466b5655ccae36f6aba6cf765d2a5afb3eb5b188d086212`
- Package wheel: `conversation_prosody_pipeline-0.1.0-py3-none-any.whl`
- Wheel SHA-256: `86c9387c9a6d55467f62ceeecce051037c6cd0b7effb910077e18f1160c23a60`
- Python: 3.13.5
- Conversion: FFmpeg 7.1.4, mono 16 kHz 16-bit PCM WAV
- Transcription: `faster-whisper` 1.2.1, `base.en`, CPU/int8, beam size 5,
  with voice activity detection enabled
- Stream simulation: 100 ms chunks

Speech-to-text tooling was installed only in the disposable experiment environment;
it was not added to the package dependencies.

## Method

For each recording, the experiment:

1. converted the MP3 to mono 16 kHz 16-bit PCM WAV;
2. generated an English transcript using external speech-to-text;
3. passed the same WAV and transcript to `ingest_wav_file` and
   `ingest_wav_stream`;
4. built metadata through a fresh `ProsodyPipeline` for each path; and
5. compared duration (tolerance `1e-6` ms), normalized RMS energy (`1e-12`), and
   transcript-derived speech rate (`1e-9` WPM).

The disposable runner was `experiments/live_action_ingest.py`. A representative run
was:

```bash
.venv/bin/python experiments/live_action_ingest.py \
  artifacts/source_media/selectedpoems_01_ragsdale_64kb.mp3 \
  --name selectedpoems_01_galatea_real_stt \
  --model base.en \
  --source-url https://archive.org/details/selectedpoems_lulahragsdale_2606_librivox
```

## Results

Four of seven recordings (57.1%) were processed, totaling 571.931 seconds
(9m 31.9s) and 1,065 transcribed words.

| Track | Duration (s) | STT words | Speech rate (WPM) | Energy RMS | File/stream |
|---|---:|---:|---:|---:|:---:|
| Galatea | 157.083 | 273 | 104.276 | 0.044454524 | match |
| Upton Rey | 158.128 | 292 | 110.796 | 0.044062410 | match |
| Promise | 117.609 | 213 | 108.665 | 0.045186867 | match |
| Outside | 139.111 | 287 | 123.786 | 0.045839201 | match |

All three compared features matched for all four recordings. This validates that, for
these inputs and chunk settings, package version 0.1.0 computes equivalent aggregate
features through its file and simulated-stream adapters.

## Interpretation limits

- The transcripts are uncorrected machine transcriptions, not verified editions.
- Speech rate is the STT word count divided by the complete recording duration, so it
  includes pauses and spoken introductions.
- Energy RMS is normalized PCM amplitude, not calibrated loudness.
- This small consistency check does not establish accuracy across codecs, recording
  conditions, languages, or streaming chunk sizes.
- The pipeline made no emotion, identity, or biometric inference.

The original detailed JSON, JSONL, CSV, reports, transcripts, and converted WAV files
remain in the disposable workspace and are intentionally not copied into the source
repository.
