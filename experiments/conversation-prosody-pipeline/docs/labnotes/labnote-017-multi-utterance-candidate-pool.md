---
schema_version: 1
id: prosody-017
title: "multi-utterance prosody candidate pool"
date: 2026-09-11
status: complete
outcome: mixed
question: "Can a small multi-utterance candidate pool supply natural repeated readings for a held-out fingerprint-retrieval test?"
tags: ["candidate-generation","conversational-prosody","dataset","prosody-fingerprint"]
lineage: ["prosody-016"]
relations: [{"target":"prosody-016","type":"extends","rationale":"Expands the positive eight-clip representation pilot across unseen lexical content before freezing retrieval."}]
publish: true
---
# Labnote 017: multi-utterance prosody candidate pool

## Question

Can a small multi-utterance candidate pool supply natural repeated readings for a
held-out fingerprint-retrieval test?

## Frozen pool

- Four previously unused conversational utterances.
- Three broad candidate recipes per utterance: calm matter-of-fact delivery, weary
  exasperation, and amused disbelief.
- One shared seed, Qwen3-TTS 1.7B CustomVoice, the `Aiden` speaker, and whole-utterance
  synthesis without post-processing.
- Exactly twelve private clips; recipe identity is hidden during annotation.
- Reuse the Prosody 015 listener ontology and 1–5 naturalness, intensity, and confidence
  scales, recording what each clip actually expresses rather than recipe compliance.

This is corpus construction, not a test of instruction following. Retrieval evaluation
will be frozen only after annotation establishes which labels the candidate pool really
contains; no held-out claim is made here.

## Result

All twelve outputs passed mechanical integrity and were blindly annotated. Six met the
4/5 naturalness floor, spanning all four new utterances. Every natural clip carried a
disbelief label; none was neutral-only. The nominally matter-of-fact recipe produced two
natural clips, but both were heard as expressive. Weary exasperation produced three
natural clips, and amused disbelief produced one.

The pool successfully expanded the natural expressive gallery across new lexical
content, but it cannot support a balanced held-out neutral-versus-expressive retrieval
test. A minimal follow-up should generate one uninstructed control per utterance and stop
after four clips rather than repeating the full pool.
