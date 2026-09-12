---
schema_version: 1
id: prosody-014
title: "contrastive-focus instruction-form ablation"
date: 2026-09-11
status: complete
outcome: negative
question: "Does removing the competing focus word from Qwen's instruction restore directional contrastive emphasis?"
tags: ["ablation","conversational-prosody","instruction-control","prosody-control","synthetic-audio"]
lineage: ["prosody-013"]
relations: [{"target":"prosody-013","type":"extends","rationale":"Tests whether the failed paired instruction made the explicitly prohibited competitor salient."}]
publish: true
---
# Labnote 014: contrastive-focus instruction-form ablation

## Question

Does removing the competing focus word from Qwen's instruction restore directional
contrastive emphasis?

## Motivation

Prosody 013 established a useful split: Qwen3-TTS cleared the naturalness floor but its
paired instructions appeared to emphasize the wrong word. Each instruction named both
the intended focus and a prohibited competitor. This pilot isolates instruction form
without changing the now-acceptable synthesis backend.

## Frozen pilot

- Same Qwen3-TTS model, `Aiden` voice, sentences, and four intended readings as 013.
- Positive-only arm: explicitly names only the intended focus word.
- Context-only arm: describes the conversational correction without naming either word.
- One shared seed per arm and condition, producing eight outputs total.
- No reference audio, cloning, fine-tuning, DSP, or changed target text.
- Generated audio, report, and admission state remain private.

Mechanical integrity requires eight distinct complete utterances between 0.8 and 8.0
seconds. Admission records naturalness and directional correctness separately for each
arm. This is a mechanism-selection ablation, not evidence of general instruction
following; any winning arm requires replication before expansion.

## Result

All eight frozen outputs were distinct, complete, and mechanically valid. The owner-local
admission review found natural-sounding examples in the set, but no output could honestly
be judged both natural and directionally correct. Neither positive-only nor context-only
instruction therefore won the mechanism-selection gate, and no blinded follow-up was
prepared.

The review still exposed useful emergent behavior. The context-only `Jordan` rendering
placed very natural-sounding sarcasm on “again,” while the positive-only `bicycle`
rendering sounded strongly and effectively exasperated. Those readings were not the
requested lexical-focus controls, but they suggest that Qwen can generate coherent
expressive variation more reliably than it can obey this word-level control scheme.

The admission interface combined naturalness and directional correctness in one checkbox,
while the operator ultimately used selections for naturalness alone and revised them.
Checkbox counts are therefore not interpreted as directional evidence; the decisive
record is the explicit report that none passed both criteria simultaneously.

This motivates a reversed architecture for later study: generate candidate readings,
characterize the prosody that actually emerged, and select against conversational intent.
That hypothesis is not tested by this labnote.
