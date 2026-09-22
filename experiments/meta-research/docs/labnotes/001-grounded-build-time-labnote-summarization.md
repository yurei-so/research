---
schema_version: 1
id: meta-research-001
title: "Grounded build-time labnote summarization"
date: 2026-09-21
status: running
outcome: pending
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

The versioned protocol is stored with the experiment in
`experiments/meta-research/experiments/meta-research-001/frozen-protocol.json`.
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

The experiment and shadow-mode apparatus are active. Results remain pending
until the frozen campaign and review are complete.

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
