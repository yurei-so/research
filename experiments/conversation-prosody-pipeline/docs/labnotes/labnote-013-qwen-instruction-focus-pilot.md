---
schema_version: 1
id: prosody-013
title: "instruction-conditioned contrastive focus"
date: 2026-09-11
status: complete
outcome: negative
question: "Can reference-free natural-language instructions produce natural, directionally correct contrastive focus?"
tags: ["blinded-review","conversational-prosody","instruction-control","prosody-control","synthetic-audio"]
lineage: ["prosody-012"]
relations: [{"target":"prosody-012","type":"extends","rationale":"Replaces failed recorded-reference conditioning with reference-free natural-language prosody instructions."}]
publish: true
---
# Labnote 013: instruction-conditioned contrastive focus

## Question

Can reference-free natural-language instructions produce natural, directionally correct
contrastive focus?

## Motivation

Prosody 012 generated eight mechanically valid F5-TTS outputs but stopped when every
output failed the owner-local naturalness floor. This pilot removes recorded reference
audio entirely instead of attempting to clean or tune around that failure. It tests a
different control channel: natural-language delivery instructions applied to a fixed
preset voice.

## Frozen pilot

- Qwen3-TTS 12 Hz 1.7B CustomVoice, English preset voice `Aiden`.
- The same two contrastive sentence pairs used in Prosody 012.
- Symmetric instructions that name the intended focus and exclude its competitor.
- Two fixed seeds per condition; eight outputs total.
- Whole-utterance generation without reference audio, cloning, fine-tuning, or DSP.
- Generated audio, reports, and review state remain private.

The run fails on missing conditions, invalid focus pairing, duplicate audio, or output
outside the frozen 0.8–8.0 second integrity range. Mechanical passage does not admit
blinded review. Every output must first sound natural and place contrastive emphasis on
the instructed word. Only a fully passing set may become a blinded context-matching
comparison.

## Result

The isolated Qwen3-TTS run generated all eight frozen outputs on an RTX 4070.
Every waveform was distinct and passed the mechanical duration gate. In owner-local
admission review, the outputs sounded substantially more natural than Prosody 012's
reference-conditioned audio, clearing the qualitative naturalness floor.

The set nevertheless failed directional admission. The operator reported that emphasis
appeared to fall on the wrong word, so the experiment stopped without a blinded review.
Generated audio, the run report, and admission state remain private.

This separates synthesis quality from focus control: reference-free instruction control
repaired the audible-quality failure but did not validate the frozen paired instruction
template. Both instructions explicitly named the intended word and its competitor. A
future experiment may test whether mentioning the competitor—especially inside a
negative instruction—made that word salient, but that explanation was not isolated here.

## Interpretation boundary

A positive result would validate only this model, preset voice, instruction template,
and tiny English corpus as worthy of expansion. It would not establish arbitrary
prosody control, speaker independence, or a production context-to-speech compiler.
