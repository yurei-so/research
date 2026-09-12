---
schema_version: 1
id: prosody-016
title: "acoustic fingerprint pilot"
date: 2026-09-11
status: running
outcome: pending
question: "Do lightweight acoustic fingerprints recover perceived emphasis and expressive delivery in the Prosody 015 corpus?"
tags: ["acoustic-analysis","conversational-prosody","prosody-fingerprint","representation"]
lineage: ["prosody-015"]
relations: [{"target":"prosody-015","type":"extends","rationale":"Measures whether deterministic acoustic descriptors recover the owner-labeled readings discovered in that corpus."}]
publish: true
---
# Labnote 016: acoustic fingerprint pilot

## Question

Do lightweight acoustic fingerprints recover perceived emphasis and expressive delivery
in the Prosody 015 corpus?

## Frozen pilot

- Reuse the eight private, blindly annotated Prosody 015 clips without synthesis or editing.
- Use `faster-whisper` `small.en` only to obtain word timestamps.
- Independently measure duration, voiced fraction, internal pauses, RMS-energy variation,
  F0 center/spread/range/slope, three-part energy and F0 contours, and word-local energy,
  duration, F0, and preceding pause.
- Define each word's prominence as the unweighted mean of its available within-utterance
  standardized word features.
- Count perceived-focus recovery when the highest-prominence aligned word appears in one
  of the annotator's comma-separated focus phrases.
- Reduce the exploratory speech-act ontology to neutral-only versus expressive-any, then
  compare between-label and within-label Euclidean distances after feature standardization.
  Evaluate the signed separation using the exact permutation distribution preserving the
  observed class counts; directional success requires positive separation and `p <= 0.10`.

The tiny corpus cannot train a classifier or validate affect recognition. This pilot asks
only whether the representation contains enough of the listener-observed structure to
justify collecting more candidates.
