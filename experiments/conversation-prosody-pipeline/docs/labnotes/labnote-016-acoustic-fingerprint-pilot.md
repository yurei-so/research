---
schema_version: 1
id: prosody-016
title: "acoustic fingerprint pilot"
date: 2026-09-11
status: complete
outcome: positive
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

## Result

All eight clips aligned to the expected transcript exactly. The untrained, equal-weight
word-prominence score recovered one of the annotator's perceived-focus phrases in five
of eight clips.

Three clips carried at least one non-neutral speech-act label and five were neutral-only.
The preregistered standardized fingerprint distance placed expressive readings farther
from neutral readings than same-label readings by 2.328 distance units. That separation
was the strongest of all 56 assignments preserving the observed 3/5 class split, giving
an exact one-sided permutation value of `1/56 = 0.0179` and passing the directional gate.

An implementation audit before interpretation found that a missing voiced contour bin
could be encoded as an extreme sentinel. Amendment 001 defined contours over the active
voiced span and replaced missing pitch with the within-clip median; the initial output
was discarded, while the frozen labels, feature families, statistic, and threshold were
unchanged.

This is positive evidence for the representation, not for a deployable recognizer. The
same listener labeled all eight clips, only two transcripts and one synthetic speaker are
represented, and the expressive class contains three examples. The next justified step
is to generate and label a larger candidate pool across more utterances, then freeze a
held-out retrieval test before fitting or selecting feature weights.
