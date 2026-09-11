---
schema_version: 1
id: prosody-012
title: "reference-conditioned contrastive-focus transfer"
date: 2026-09-11
status: complete
outcome: negative
question: "Can whole-utterance reference conditioning reproduce an explicitly demonstrated contrastive focus without the artifacts of post-hoc DSP?"
tags: ["blinded-review","conversational-prosody","prosody-control","reference-conditioning","synthetic-audio"]
lineage: ["prosody-009","prosody-010"]
relations: [{"target":"prosody-009","type":"extends","rationale":"Retains artifact-free whole-utterance generation while replacing unreliable lexical-stress mapping with an explicit spoken reference."},{"target":"prosody-010","type":"motivated-by","rationale":"Prosody 010 showed that native primary-versus-secondary stress did not reliably create directional discourse prominence."}]
publish: true
---
# Labnote 012: reference-conditioned contrastive-focus transfer

## Question

Can whole-utterance reference conditioning reproduce an explicitly demonstrated
contrastive focus without the artifacts of post-hoc DSP?

## Motivation

Prosody 008 rejected token-local DSP because an obvious voice artifact survived its
numerical acoustic gates. Prosody 009 restored natural whole-utterance audio but did
not validate its focus mapping, and Prosody 010 showed why: lexical stress did not
reliably create directional acoustic prominence.

This pilot changes the control channel rather than retrying that mechanism. A consenting
speaker demonstrates each intended reading directly. A local reference-conditioned
model then regenerates the unchanged sentence from the paired reference. The test asks
whether the demonstrated focus survives generation; it does not claim independent
control of speaker identity and prosody.

## Frozen pilot

- Two authored contrastive pairs from the existing Prosody 004 corpus.
- Two focus readings per sentence, privately recorded by one consenting speaker.
- F5-TTS v1 Base, two fixed seeds per reading, eight outputs total.
- Exact reference transcript and generation text are identical.
- Whole-utterance generation only; no splicing, pitch shifting, gain editing, time
  stretching, or other post-processing.
- References, generated audio, manifests, and review state remain private.

The run fails on changed reference digests, unsafe WAV structure, duplicate outputs, or
excessive duration drift. Passing those checks does not admit human review. The audio
must next pass explicit naturalness and directional focus-localization checks. Only then
may a blinded forced-choice bundle ask which word was emphasized.

## Result

The isolated F5-TTS run generated all eight frozen outputs on an RTX 4070. All files
were distinct and passed the corrected mechanical integrity gate. The duration check
was amended before listening because interactive reference recordings included the
time spent waiting for the operator's completion message; total reference duration was
therefore not a valid denominator for generated utterance duration.

The owner-local admission review stopped the experiment. Across the eight outputs, the
operator sometimes heard a slight reverberant effect and did not judge any output truly
natural. Because naturalness was a prerequisite, directional focus localization was not
scored and no blinded forced-choice bundle was prepared. Private references, generated
audio, manifests, and admission state remain unpublished.

This is a negative result for this bounded same-speaker F5-TTS reference-conditioning
mechanism, not evidence against reference-conditioned synthesis in general. A follow-up
should change the control channel rather than tune around the failed gate—for example,
instruction-conditioned whole-utterance synthesis without a recorded style reference.

## Interpretation boundary

Reference conditioning may entangle voice, recording conditions, and global style. A
positive pilot would establish only that this bounded same-speaker method deserves a
larger independent-listener test. It would not show general speaker-independent prosody
transfer or validate a production compiler.
