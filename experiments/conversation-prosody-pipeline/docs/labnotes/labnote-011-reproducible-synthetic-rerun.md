# Lab note: Reproducible synthetic conversational-audio rerun

**Run date:** 2026-08-23  
**Status:** Completed; automatic result negative/inconclusive

## Question

Does the negative Labnote 003 matched-versus-shuffled result persist when every audio
clip is generated locally by a known, fingerprinted synthesizer and exact transcript
fidelity is verified before downstream generation?

## Correction carried forward

Labnote 003 consumed opaque third-party audio whose synthesis model, voice,
conditioning, prompt, seed, code, license, and human validation were not disclosed.
That audio is quarantined. This rerun uses only the first 20 rows' text and labels from
the pinned public dataset revision; it never reads the dataset audio field. Because
the dataset license remains undisclosed, the external text snapshot and all generated
artifacts stay outside source control.

## Synthesis contract

- `hexgrad/Kokoro-82M`, locally cached and package-fingerprinted;
- voice `af_heart`, speed 1.0, 24 kHz PCM;
- one complete synthesis call per `rewritten_text`;
- no segmentation, splicing, gain, pitch shifting, time stretching, or other DSP;
- WAV, source-snapshot, package, and generated-token fingerprints retained; and
- no claim that neutral Kokoro delivery realizes dataset emotion or intent labels.

The whole-utterance/no-DSP choice carries forward the naturalness lesson from
Labnote 009. Labnote 010 showed that native stress annotation does not reliably create
directional discourse prominence, so stress markup is deliberately excluded.

## Preregistered gates

Downstream LLM generation is forbidden unless:

1. independent ASR exactly matches normalized `rewritten_text` for all 20 clips; and
2. at least 18 of 20 deterministic next-row matched/shuffled cue pairs differ.

If either gate fails, the failure is the result. If both pass, reproduce Labnote 003's
five conditions with the same system prompt, temperature 0.4, seed 42, and
deterministic next-row cue derangement. The historical `qwen2.5:3b` model is no longer
installed on mpai; the rerun therefore preregisters the available `qwen3:8b` successor
and records this as a model-generation change rather than claiming a strict replication.
The label condition remains an unfair reference control and must not be interpreted as
synthesized prosody.

## Execution

Agent Runtime submitted each phase to roostd as a non-preemptive experiment workload.
The synthesis phase completed as run `4f24fd61-4411-4e8b-87d1-b62ea7d1c33a`.
Independent local `faster-whisper` `small.en` transcription then evaluated the frozen
WAVs. The first downstream attempt, run `ca0605f3-48c9-41ac-ac18-f4c66096c91a`,
failed before retaining a response because the historical `qwen2.5:3b` model was not
installed. The explicitly revised, checkpointed `qwen3:8b` run
`3f3e9ac5-66bc-4676-a67c-7ca0a0856542` completed 100 responses with exit code zero.

Reproducibility facts:

- dataset revision: `3d49be1a3f15b3f58817ea86918584b5656f3a6e`;
- source snapshot SHA-256: `7c9f7abb23649b7275ab020792b552ba25d8b21966fe25dddb63437d7235675c`;
- source dataset audio used: no;
- Kokoro/Misaki: 0.9.4/0.9.4;
- synthesis voice/speed: `af_heart`/1.0;
- downstream model: `qwen3:8b`, local digest
  `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`.

## Gate results

- transcript fidelity: 20/20 exact after lowercase alphanumeric normalization;
- matched/shuffled cue separation: 20/20 bundles differed; and
- frozen WAV integrity: every synthesis hash was reverified before generation.

Both preregistered gates passed.

## Automatic response diagnostics

| Condition | Rows | Mean response words | Explicit cue-language responses |
|---|---:|---:|---:|
| A: original only | 20 | 90.30 | 2 |
| B: rewritten only | 20 | 70.85 | 0 |
| C: rewritten + matched cues | 20 | 78.25 | 1 |
| D: rewritten + shuffled cues | 20 | 86.90 | 0 |
| E: rewritten + dataset labels | 20 | 77.00 | 2 |

Mean token-set Jaccard similarity was 0.239 for A versus B, 0.299 for B versus C,
0.289 for B versus D, and 0.301 for C versus D. Matched and shuffled cue blocks both
changed output relative to rewritten text. The matched condition was not uniquely
closer to the text-only response and produced shorter responses than the shuffled
condition. These are behavior-change diagnostics, not empathy or quality measures.

## Result

The provenance repair succeeded: this run has exact text/audio fidelity, immutable
audio hashes, a known synthesizer, and genuinely distinct matched/shuffled cue blocks.
The automatic downstream result nevertheless remains negative/inconclusive. Nothing
in these proxies demonstrates that correctly matched neutral-synthesis cues help more
than shuffled cues. Human review would be required for a conversational-quality claim,
but the prior result no longer depends on unknowable third-party audio generation.
