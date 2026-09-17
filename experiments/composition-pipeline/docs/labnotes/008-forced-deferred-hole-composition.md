---
schema_version: 1
id: composition-008
title: "Forced deferred-hole composition pilot"
date: 2026-09-17
status: complete
outcome: negative
question: "Does deferring one locally uncertain span until right-hand context exists improve bounded composition over direct generation or unrestricted two-pass revision?"
tags: ["blinded-review","composition","deferred-infill","negative-result"]
lineage: ["composition-007"]
relations: [{"target":"composition-007","type":"extends","rationale":"Continues the search for useful inference-time composition structure after extended thinking failed to justify its cost."}]
publish: true
---
# Labnote 008: Forced deferred-hole composition pilot

## Question

Does deferring one locally uncertain span until right-hand context exists improve bounded
composition over direct generation or unrestricted two-pass revision?

## Frozen protocol

The pilot used `qwen3:8b` at temperature zero on eight authored rewrite tasks. Every task
had three matched arms:

- `direct`: one preservation-first rewrite call;
- `full-revision`: the same direct call followed by one unrestricted revision call; and
- `deferred-infill`: one draft forced to contain exactly one typed
  `[[DEFER_1:TYPE]]` hole, followed by a hole-only infill call.

The runtime, not the model, validated and replaced deferred tokens. A valid deferred
draft had exactly one declared hole and at least 24 non-whitespace characters of
right-hand context. The infill response could provide only a bounded replacement;
nested or unresolved holes failed the trial. This required no tokenizer changes,
training, or privileged decoding hooks.

The unrestricted revision arm controlled for the deferred arm's second model call.
Review was preregistered as two separate blinded comparisons per complete case: direct
versus deferred infill, then full revision versus deferred infill. A review gate required
at least six complete three-arm cases. Raw prompts, candidates, checkpoints, mappings,
and judgments remain owner-private.

Before review, intake discovered that the existing text-review envelope supported only
one binary arm mapping per bundle. No generation was repeated or changed. A recorded
amendment split the same sealed candidates into two binary review sessions and added a
text-envelope version that names both arms while preserving blinding, deterministic
counterbalancing, and append-only judgments.

## Result

The campaign completed all 24 planned trials. Twenty-three succeeded; the deferred arm
for one case failed its structured protocol after the allowed retry. Seven complete
three-arm cases remained, passing the six-case review gate. There were no automatic
ties, leaving seven judgments in each blinded review session.

| Arm | Successful trials | Mean calls | Mean latency | Mean generated tokens | Mean final characters |
| --- | ---: | ---: | ---: | ---: | ---: |
| Direct | 8/8 | 1 | 0.911 s | 38 | 221.1 |
| Full revision | 8/8 | 2 | 1.368 s | 80 | 235.1 |
| Deferred infill | 7/8 | 2 | 1.787 s | 112 | 237.9 |

In the first review, direct composition was preferred in six of seven cases; deferred
infill won one, with no ties. In the matched-call comparison, full revision was preferred
in all seven cases; deferred infill won none, with no ties. The latter 7–0 result has an
exact one-sided sign-test probability of 1/128 under an equal-preference null. Because
one reviewer judged a small authored corpus, this is a bounded result rather than a
general population estimate.

Post-reveal inspection found a consistent structural failure. Deferred candidates often
retained an incorrect source sentence, continued past it, and used the local infill to
append a corrective contrast. The final text therefore contained both the original false
claim and its attempted correction. Several candidates also produced malformed joins
around the filled span. A hole-only second pass could improve its local replacement but
could not revise the globally committed structure around it.

## Disposition

This is a negative result for forced single-hole deferred infill in bounded rewriting.
It was slower and used more generated tokens than unrestricted two-pass revision while
losing every matched-call judgment. Do not add this mechanism to the production
composition path and do not repeat this corpus with more holes or a larger token budget.

The result does not establish that all deferred decoding is harmful. A materially
different future mechanism would need to avoid freezing incorrect surrounding text—for
example, allowing a later structural rewrite, generating from a plan with unresolved
semantic slots, or integrating uncertainty into decoding rather than imposing a textual
hole. Such a mechanism should be treated as a new experiment, not a repair of this run.
