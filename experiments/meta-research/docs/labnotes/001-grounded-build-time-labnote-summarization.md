---
schema_version: 1
id: meta-research-001
title: "Grounded build-time labnote summarization"
date: 2026-09-21
status: complete
outcome: positive
question: "Can a versioned AI apparatus produce concise labnote orientations that preserve findings, limitations, and negative results without introducing unsupported claims?"
tags: ["meta-research","summarization","apparatus","provenance","human-review"]
lineage: []
relations: []
publish: true
---
# META-RESEARCH-001: Grounded build-time labnote summarization

## Question

Can a versioned AI apparatus produce concise labnote orientations that preserve
findings, limitations, and negative results without introducing unsupported
claims?

## Motivation

The public research library should help humans and agents decide whether a
labnote is relevant without replacing its canonical Markdown source. A summary
generator may help, but it may also erase caveats, overstate mixed evidence, or
invent claims. Those risks require an experiment before site integration.

## Frozen protocol

The original frozen protocol and its superseding v2 protocol are stored with
the experiment. The v1 file remains immutable so the stopped pilot can be
reproduced; `frozen-protocol-v2.json` governs the replacement campaign.
Candidate summaries are generated from public canonical labnotes in shadow
mode. Generation does not modify labnotes, the public manifest, or `dist/`.

Each candidate must include a short orientation, the central finding,
limitations, negative or mixed evidence, and explicit source quotations used as
evidence. Deterministic validation checks the schema, source hash, length,
quotation support, and no-new-claims acknowledgement before human review.

The frozen corpus deliberately includes positive, negative, mixed,
inconclusive, and apparatus-oriented records. Reviewers judge claim support,
finding preservation, caveat retention, negative-result retention, and whether
the candidate is useful for a relevance decision. Accepted, edited, and
rejected candidates all remain experimental observations.

## Promotion gate

The apparatus is not production research infrastructure yet. Promotion into
`research-tools` requires completed META-RESEARCH-001 evidence, a documented failure
policy, and a separate reviewed change. Public rendering requires an additional
activation decision; generation success alone never authorizes publication.

## Current status

The first shadow campaign stopped before human scoring due to a construct
mismatch. Its candidates were concise and grounded, but behaved like compressed
abstracts: they made the reader process a smaller version of the labnote instead
of quickly answering why the note exists and what changed.

The original protocol and artifacts remain frozen as failed-pilot evidence.
The superseding v2 protocol narrows the reader-facing contract to exactly two
sentences: the first states the question or causal premise; the second states
the observed effect and practical implication. Supporting quotations and
provenance do not expand the reader-facing orientation. V2 does not require the
model to extract citations; the apparatus retains the complete source hash and
generation provenance, while human review remains responsible for fidelity.

Any future public rendering must mark the text as generated without demanding
attention. The proposed treatment is a muted inset panel with clipped corners,
lower-contrast text, and a compact `AI ORIENTATION · EXPERIMENTAL` label. This
separates it from canonical authored prose while keeping it easy to ignore.

## Second supervised shadow observation

All eight v2 candidates passed the two-sentence structural validator. Human
review nevertheless scored every candidate zero across all five dimensions.
The imposed shape had produced tiny abstracts rather than conversational
orientations: terms such as “bounded-span,” “directionally correct,” and
“preregistered gates” remained compact but did not help a reader understand the
work quickly. The v2 promotion gate therefore failed with zero acceptable
candidates and median relevance utility zero.

V3 adds a translation-register requirement called Crayon Speak. Its governing
test is whether the orientation could be said naturally to a technically
curious friend who has no project vocabulary. It keeps exactly two sentences,
requires one main idea in each, and replaces research shorthand with what the
term means. Length, jargon, parentheses, and acronym checks are warnings rather
than hard readability formulas; grounding and effect fidelity remain human
review gates.

V3 review is binary by design. The reviewer accepts an orientation if it helps
them understand the note quickly, or rejects it with a reason. The earlier
five-score form was removed because it added bookkeeping without clarifying the
actual product decision.

## Result

All eight v3 candidates passed the structural checks without language warnings,
and the human reviewer accepted all eight as useful for understanding their
source notes quickly. The frozen gate required at least seven acceptances, so
the v3 campaign passed.

The experiment therefore supports Crayon Speak as the generation contract for
a reusable orientation apparatus. It does not activate generated text on the
public site: toolkit promotion and public rendering remain separate reviewed
changes, as required by every protocol version.

## Initial supervised shadow observation

The first supervised candidate targeted the negative `composition-009` record rather
than an easy positive result. The initial validation failed closed because two
exact evidence quotations crossed Markdown line wraps. No source or public-site
file was modified. Apparatus revision `0.1.0` was corrected to normalize textual
whitespace before exact quotation comparison while retaining rejection of
invented wording. The candidate then passed schema, quotation-support, length,
claim-acknowledgement, and source-hash validation and became ready for human
review. That result does not itself establish factual grounding.

This is evidence that the shadow boundary and one deterministic check work; it
is not evidence that summaries are generally faithful or useful. The campaign
and human review remain required.
