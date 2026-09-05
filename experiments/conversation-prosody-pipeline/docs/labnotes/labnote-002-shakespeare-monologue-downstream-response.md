# Lab note: Shakespeare monologue downstream-response pilot (v0.3.1)

**Run date:** 2026-07-01  
**Package:** `conversation-prosody-pipeline` 0.3.1  
**Metadata schema:** 1.0  
**Status:** Failure

The software run completed, but the experiment failed to demonstrate that correctly
matched delivery cues improve LLM responses relative to transcript-only or
shuffled-cue controls.

## Question

Does adding delivery/prosody information to a transcript improve or meaningfully
change an LLM's conversational response?

## Setup

The experiment ran outside the package source tree in the disposable workspace
`~/Downloads/workspace/experiment`. It used all 15 recordings from the provided
LibriVox *Shakespeare Monologues, Volume 1* archive. These public-domain theatrical
readings provide real spoken audio for a smoke test, but they are not conversation.

- Input archive: `shakespeare_monologues_vol_1_librivox.zip`
- Input archive SHA-256: `4d053728b26fd5002e01c4c67a3d663657a41b4430b71e8785befffb926b31ed`
- Source download URL: not recorded in the available artifacts
- Package wheel: `conversation_prosody_pipeline-0.3.1-py3-none-any.whl`
- Wheel SHA-256: `3d84b573bad316067f37ce1178885ff1fecdf664b8ddee8fc0fc3d31932ec5b6`
- Base runner SHA-256: `4a4c6879ae948a5cc5038aa7d61a943fb81197ea2b993f082d9857a37eb68b7f`
- Reduced runner SHA-256: `42b9532bf74c302cb2b477913391de154049a751b7d322b90c5ca575eae038c0`
- Requirements SHA-256: `ff36e835f1d684c8d5d4519d8b1d894a85a12d090c99b9c24bab69af10773199`
- Python: 3.13.5
- Conversion: FFmpeg 7.1.5, mono 16 kHz 16-bit PCM WAV
- Transcription: `faster-whisper` 1.2.1, `small.en`, English, CPU/int8,
  beam size 5, word timestamps and voice activity detection enabled
- Python requirements: `faster-whisper>=1.1,<2`, `numpy>=2,<3`
- LLM runtime: Ollama
- LLM: `qwen2.5:3b`
- Generation: temperature 0.4, seed 42, non-streaming chat completion
- Metadata observations: duration, transcript-derived speech rate, normalized RMS
  energy, internal pauses, pitch variability, energy variability, hesitation count,
  interruption count, and STT confidence

The same system prompt was used for every response:

> You are speaking naturally with this person. Respond as a supportive
> conversational companion. Do not summarize what they said. Instead, continue the
> conversation naturally while respecting the speaker's emotional state, confidence,
> uncertainty, pacing, and conversational intent.

The exact dependency versions used for the completed run are recoverable only where
listed above; `requirements.txt` uses ranges rather than a lock file. Reproduction
should retain the hashes and record a fresh environment freeze.

## Method

The base runner was executed first:

```bash
cd ~/Downloads/workspace/experiment
python run.py
```

For each recording, `run.py`:

1. extracted audio from the data archive;
2. converted MP3 to mono 16 kHz 16-bit PCM WAV with FFmpeg;
3. transcribed English speech with `faster-whisper`;
4. passed the WAV and transcript to `ingest_wav_file`;
5. built schema 1.0 output with a fresh `ProsodyPipeline`;
6. added separately labeled STT timing/confidence and lightweight acoustic
   observations;
7. generated transcript-only condition A and structured-data condition B with the
   same LLM settings; and
8. saved transcripts, pipeline output, prompts, responses, and a report.

The confound-reduced runner was then executed:

```bash
cd ~/Downloads/workspace/experiment
python run_reduced.py
```

It reused the saved transcripts and observations and generated three conditions:

- **A — transcript only:** the transcript appears once and no delivery cues are
  supplied.
- **B — real delivery cues:** the same transcript appears once, followed by a compact
  `Observed delivery cues` block containing mean internal pause, maximum internal
  pause, speech rate, pitch variability, energy variability, and STT confidence.
- **C — shuffled delivery cues:** the transcript appears once, followed by the full
  cue bundle from the next recording in sorted order; the final recording wraps to
  the first. This deterministic derangement tests whether correct cues help more than
  the presence of extra structured text.

The reduced prompts do not expose `CPP`, `metadata`, `prosody pipeline`, raw JSON, or
the control assignment to the model. Every condition uses the same model, system
prompt, temperature, and seed. Responses already present in `responses_reduced/` are
reused on rerun, so delete or relocate those files only when an intentionally fresh
generation is required.

The current experiment snapshot excludes `.venv`, `.uv-cache`, `__pycache__`, and
generated Python cache files. No packaged experiment archive was available to verify
archive-specific exclusions.

## Results

All 15 recordings completed with zero reported processing failures. They total
1,640.668 seconds (27m 20.7s), and the saved STT timing output contains 3,228 words.

| Run | Conditions | Prompt files | Response files | Mean A comparison | Explicit cue language |
|---|---|---:|---:|---:|---:|
| Take 1 | A: transcript; B: transcript plus raw structured output | 30 | 30 | A vs B: 0.09 | Not consistently used |
| Take 2 | A: transcript; B: real compact cues; C: shuffled compact cues | 45 | 45 | A vs B: 0.07; A vs C: 0.09 | B: 3/15; C: 3/15 |

The Take 1 report found that extra pipeline data changed generated wording but did not
show a reliable quality improvement. It also identified transcript duplication in B,
implementation-oriented labels, raw data volume, and the lack of a control for merely
adding structured text.

Take 2 removed those prompt confounds and added condition C. Both B and C differed
substantially from A. The simple report-level keyword check found delivery-related
language in the same number of real-cue and shuffled-cue responses. This does not show
that B is more empathetic, natural, or appropriately aligned than A or C.

The evaluation file `reports/evaluation_confound_reduced.jsonl` contains 45 rows with
responses, randomized display labels, and blank empathy, naturalness, cue-alignment,
and overinterpretation fields. No human scores have been entered, so response quality
has not been measured.

## Comparison with the Selected Poems real-media note

The earlier *Selected Poems real-media ingest (v0.1.0)* lab note answers a different,
lower-level question.

| Aspect | Selected Poems note | Shakespeare pilot |
|---|---|---|
| Package | 0.1.0, schema 1.0 | 0.3.1, schema 1.0 |
| Dataset | Four LibriVox Sidney Lanier poetry recordings | Fifteen LibriVox Shakespeare monologues |
| Question | Do file and simulated-stream paths agree? | Do delivery cues improve downstream responses? |
| STT | `base.en`, CPU/int8 | `small.en`, CPU/int8 |
| Comparison | File ingest vs 100 ms simulated stream | Transcript-only vs real cues vs shuffled cues |
| Result | Duration, RMS energy, and speech rate matched | Responses changed; real cues did not clearly outperform controls |

The Selected Poems result validates adapter consistency for its inputs and chunk
settings. It does not establish downstream usefulness. The Shakespeare pilot tests
downstream behavior but does not repeat file-versus-stream equivalence, so it is not a
streaming regression test. Together, the notes show progression from ingest
consistency to a first controlled usefulness test; neither establishes conversational
efficacy.

## Interpretation limits

- Shakespeare monologues are theatrical performances, not conversation turns.
- The task encourages literary explanation or summary even though the system prompt
  asks the model not to summarize.
- LibriVox titles, reader credits, and end-of-reading boilerplate remain in some
  transcripts and may affect responses.
- Transcripts are uncorrected STT output, not verified Shakespeare editions.
- Speech rate divides STT word count by complete recording duration and therefore
  includes silence, introductions, and outros.
- Normalized RMS and energy variability are not calibrated loudness.
- Raw numeric cues may be hard for the LLM to interpret without qualitative bins or
  within-speaker reference values.
- Every recording starts a fresh pipeline baseline. Conversation-local deltas are
  empty, and multi-turn adaptation is not exercised.
- The saved JSONL is not fully blinded: `condition` and `blinded_label` appear in the
  same row, and rows are ordered A/B/C within each filename.
- No human blinded ratings have been completed.
- Text similarity and keyword presence measure change, not conversational quality.
- Only one LLM, one generation per condition, and one fixed seed were tested.
- Shuffled cues are plausible mismatched bundles, not synthetic, contradictory, or
  adversarial cue combinations.
- The pipeline made no emotion, identity, or biometric inference.

## Next steps

1. Export a truly blinded rater sheet and a separate answer key.
2. Strip or mark LibriVox title, reader-credit, and outro boilerplate.
3. Convert numeric cues into calibrated qualitative descriptions relative to a
   within-speaker baseline while retaining raw values for analysis.
4. Collect blinded scores for empathy, naturalness, cue alignment, and
   overinterpretation; compare B against both A and C.
5. Test multi-turn conversation datasets with timing and speaker annotations. Candidate
   datasets include HarperValleyBank, HCRC Map Task, AMI Meeting Corpus, and Santa
   Barbara Corpus, subject to licensing and annotation review.
6. Add a same-text/different-delivery experiment using short utterances such as
   "I guess that's fine." to hold lexical content constant.
7. Pin exact Python dependencies and save the Ollama model digest with the next run.

## Bottom line

The run successfully validated the experiment plumbing and showed that adding cue
text changes generation. Its research status is **Failure** because correctly matched
delivery cues did not demonstrably improve responses over transcript-only or shuffled
controls. A conversation-based dataset and completed blinded ratings are required for
the next meaningful test.
