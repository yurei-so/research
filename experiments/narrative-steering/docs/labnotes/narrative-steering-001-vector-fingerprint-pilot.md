---
schema_version: 1
id: narrative-steering-001
title: "Matched-state narrative steering vector pilot"
date: 2026-09-05
status: planned
outcome: pending
question: "Can blinded ratings of continuations from matched narrative states recover a repeatable directional steering vector for each model, distinct from story and prompt effects?"
tags: ["human-review","model-comparison","narrative-steering","panel-recognition","prosody-control","story-engine"]
lineage: []
publish: true
---
# Labnote 001: Matched-state narrative steering vector pilot

## Question

Can blinded ratings of continuations from matched narrative states recover a
repeatable directional steering vector for each model, distinct from story and
prompt effects?

## Scope

This pilot tests measurement, not a grand theory of narrative geometry. The
fingerprint is a seven-coordinate descriptive vector. It is not an emotion
classifier, quality score, personality diagnosis, or claim that a model has a
single context-independent policy.

The cone visualization proposed in Whiteboard #2281 is explicitly deferred.

## Vector

Each coordinate uses a signed five-point scale from `-2` to `2`; zero means the
continuation preserves or does not materially push the supplied state.

| Coordinate | Negative direction | Positive direction |
| --- | --- | --- |
| `agency` | overrides or bypasses protagonist choice | preserves or reinforces protagonist choice |
| `affect` | pushes distress, shame, fear, or despair | pushes comfort, reassurance, or positive reinterpretation |
| `social` | isolation, hostility, or withdrawal | help, protection, competence, or reconciliation |
| `causal_fortune` | introduces convenient obstacles or losses | introduces convenient assistance or rescue |
| `closure` | prolongs or opens additional unresolved motion | stabilizes, resolves, rests, feeds, or sends characters to safety |
| `escalation` | reduces intensity or stakes | increases intensity, danger, or dramatic stakes |
| `intimacy` | increases emotional distance | increases romance, attachment, or interpersonal intimacy |

Reviewers also record confidence from `1` to `3`. Quality is intentionally not
part of the vector: polished prose can still steer strongly, and awkward prose
can preserve the state.

## Frozen pilot

- Four authored story states spanning domestic, expedition, political, and
  mystery contexts.
- Two prompt variants per state: neutral continuation and an explicit agency
  guard.
- Three models selected before generation.
- Two independent samples per model/state/variant cell.
- Forty-eight total continuations and forty-eight blinded judgments.
- Fixed generation parameters and maximum continuation length across models.
- Model identity hidden until every judgment is locked.

The agency guard is not treated as a better prompt. It is a controlled
perturbation used to measure how much each model's vector rotates when the
instruction explicitly protects protagonist choice and affect.

## Analysis

For each model, report:

1. Raw mean vector and standard error.
2. Matched-cell-centered vector after subtracting the across-model mean for the
   same state, prompt variant, and sample index.
3. Agency-guard minus neutral vector shift.
4. Per-state vectors and disagreement; no aggregate fingerprint is considered
   stable when directions reverse freely across states.

No dimension selection, scale changes, prompt edits, dropped continuation, or
model substitution is allowed after generation begins. Missing or malformed
cells invalidate the pilot rather than being silently omitted.

## Promotion gate

This pilot earns a larger preregistered study only if:

- every frozen cell and blinded judgment is complete;
- at least one coordinate shows the same signed model ordering in at least
  three of four neutral states; and
- the ordering is not explained solely by one malformed output or a single
  reviewer confidence-1 judgment.

A passed gate demonstrates that the apparatus detects a candidate repeatable
signal. It does not validate the coordinate ontology or justify the deferred
cone visualization.
