---
schema_version: 1
id: prosody-014
title: "contrastive-focus instruction-form ablation"
date: 2026-09-11
status: planned
outcome: pending
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
