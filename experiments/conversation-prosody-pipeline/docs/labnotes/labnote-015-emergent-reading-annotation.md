---
schema_version: 1
id: prosody-015
title: "emergent prosody annotation"
date: 2026-09-11
status: complete
outcome: mixed
question: "What coherent readings actually emerge when direct lexical-focus control fails?"
tags: ["annotation","conversational-prosody","discovery","prosody-fingerprint","synthetic-audio"]
lineage: ["prosody-014"]
relations: [{"target":"prosody-014","type":"extends","rationale":"Reframes its natural but misdirected outputs as specimens to characterize rather than failed commands to discard."}]
publish: true
---
# Labnote 015: emergent prosody annotation

## Question

What coherent readings actually emerge when direct lexical-focus control fails?

## Motivation

Prosody 014 produced no clip that simultaneously passed naturalness and requested focus,
but it did produce compelling unrequested performances: natural sarcasm on “again” and
effective exasperation in another reading. This suggests reversing the architecture.
Rather than treating synthesis as a deterministic prosody compiler, generate candidates,
characterize their actual delivery, and later retrieve the candidate whose observed
fingerprint best fits conversational intent.

## Frozen annotation pass

- Reuse exactly the eight private Prosody 014 outputs; generate no new audio.
- Randomize their order and hide source condition, instruction arm, intended focus, and
  conversational context until every annotation is locked.
- Record perceived focus, one or more speech acts, one or more affects, intensity,
  naturalness, confidence, and an optional observation.
- Keep audio, annotations, hashes, and reveal mapping owner-local and private.
- Treat this as corpus characterization, not evaluation of the original instructions.

The result can motivate a later acoustic-fingerprint or retrieval experiment. Eight
single-speaker clips cannot validate a classifier, establish a stable ontology, or show
that conversational intent can already select the correct performance.

## Result

The owner completed all eight blind annotations. Seven clips scored at least 4/5 for
naturalness, and three scored 5/5, confirming that useful performances survived the
failed direct-control experiment. Only two of eight perceived-focus labels named the
requested word, however, so the original instruction still did not reliably determine
what the voice emphasized.

The annotations recovered coherent unintended readings rather than undifferentiated
failure. The positive-only `bicycle` condition was heard as natural exasperation focused
around “borrowed” and “again.” The context-only `Jordan` condition was heard as highly
natural exasperation, disbelief, and resignation focused on “again.” Five other readings
were primarily neutral statements, while one was ambiguous among correction, sarcasm,
and neutral delivery and received the lowest naturalness and confidence scores.

Context-only outputs averaged 4.5/5 naturalness versus 3.75/5 for positive-only outputs
in this eight-clip set. That difference is descriptive only: the sample is tiny, uses one
speaker and fixed seeds, and was designed to discover labels rather than compare arms.
The result supports the next measurement slice—extracting acoustic timing, pitch, and
energy descriptors and testing whether they recover these observed labels—without yet
supporting a classifier or production selector.
