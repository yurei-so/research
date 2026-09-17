---
schema_version: 1
id: composition-009
title: "Readiness-gated bounded-span repair"
date: 2026-09-17
status: complete
outcome: negative
question: "Can suffix-triggered readiness plus bounded-span repair recover the deferred-composition idea without freezing incorrect surrounding structure?"
tags: ["blinded-review","composition","deferred-infill","negative-result","readiness"]
lineage: ["composition-008"]
relations: [{"target":"composition-008","type":"extends","rationale":"Tests whether explicit readiness and whole-span repair address the structural failure observed in forced single-hole infill."}]
publish: true
---
# Labnote 009: Readiness-gated bounded-span repair

## Question

Can suffix-triggered readiness plus bounded-span repair recover the deferred-composition
idea without freezing incorrect surrounding structure?

## Frozen protocol

The experiment used `qwen3:8b` at temperature zero on eight new authored rewrite tasks.
Each task had three matched arms:

- `hole-only`: the known-negative single-hole method from Labnote 008;
- `readiness-span`: one provisional span, one to three model-declared readiness
  conditions, substantive right-hand context through an explicit readiness boundary,
  and a second call allowed to replace the complete provisional span; and
- `full-revision`: a direct rewrite followed by unrestricted revision.

The runtime owned marker assembly and deterministic replacement. The model returned
typed fields for the prefix, provisional span, right context through readiness, readiness
signal, and suffix. The emitted readiness signal was an observable protocol event, not a
measurement of hidden confidence. Review was preregistered as two separate blinded
comparisons per complete triplet: hole-only versus readiness-span, followed by
full-revision versus readiness-span. At least six complete triplets were required.

Two content-blind apparatus pilots preceded the valid campaign. The first asked the
model to place literal markers inside a JSON string; the model omitted them and the stop
rule fired after three readiness validation failures. The second moved boundaries into
typed fields, but the model redundantly echoed old markers inside three prose fields;
five complete triplets missed the six-triplet review gate. The final parser
canonicalized only redundant wire tokens before runtime-owned marker assembly. All 48
Composition tests passed, both failed pilots were preserved separately, and no pilot
candidates entered review.

Raw prompts, candidates, checkpoints, arm mappings, judgments, and the failed pilot
states remain owner-private.

## Result

The valid campaign completed all 24 planned trials without failure. All eight complete
triplets entered both blinded review sessions, with no automatic ties.

| Arm | Successful trials | Mean calls | Mean latency | Mean generated tokens | Mean final characters |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hole-only | 8/8 | 2 | 1.784 s | 112.5 | 249.0 |
| Readiness-span | 8/8 | 2 | 3.238 s | 229.6 | 623.6 |
| Full revision | 8/8 | 2 | 1.300 s | 73.4 | 209.8 |

Readiness-span was preferred to hole-only in five of eight cases; hole-only won three,
with no ties. This is directional evidence that readiness plus whole-span repair improved
on the original mechanism, not a decisive small-sample advantage.

Full revision was preferred to readiness-span in all eight cases, with no ties. The
exact one-sided sign-test probability is 1/256 under an equal-preference null. Because
one reviewer judged a small authored corpus, this remains a bounded result rather than a
general population estimate.

Post-reveal inspection aligned with the reviewer's independent observations. Readiness
outputs were roughly 2.5 times longer than either control and frequently repeated source
claims or entire revised passages. One candidate copied the task instruction into its
answer; another expanded a concise causal correction into a long checklist. Several
introduced sentence-initial capitalization errors, contradictory claims, or unnecessary
restatement. Explicit readiness provided more context to the repair call, but did not
constrain the model to use that context economically or preserve global coherence.

## Disposition

This is a negative result for readiness-gated bounded-span repair as a production
composition mechanism. It partially recovers the failed hole-only idea, but costs more
latency and generated tokens while losing every judgment to unrestricted revision. Do
not add it to the production composition path and do not repeat this corpus with a larger
token budget.

The useful result is narrower: explicit typed boundaries are a reliable way to transport
deferred state, while a model-declared readiness event alone is not sufficient editorial
control. A future experiment would need a distinct mechanism that limits repetition and
global drift—such as a compact semantic plan or deterministic postcondition—not another
variation of textual deferred repair.
