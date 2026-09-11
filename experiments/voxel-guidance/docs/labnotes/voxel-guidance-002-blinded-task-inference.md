---
schema_version: 1
id: voxel-guidance-002
title: "Blinded current-task inference"
date: 2026-09-10
status: complete
outcome: positive
question: "Can the current Minecraft task be inferred from causal behavior while holding out an entire seed block?"
tags: ["behavioral-telemetry","classification","grouped-validation","minecraft","positive-result"]
lineage: ["voxel-guidance-001"]
publish: true
---
# Labnote 002: Blinded current-task inference

## Question

Can the current task—acquire, construct, explore, or recover—be inferred from
the already-collected pilot streams without exposing the label or relying on a
world-specific split?

## Method

This exploratory follow-up uses the 12 accepted `pilot-v2` sessions. At 30,
60, 120, 240, and 480 seconds, it compiles only causal events observed by that
time. Task IDs, objective text, schedule position, world identity, and manual
markers are excluded from model inputs. Forced death events are not features;
death-triggered inventory churn is excluded until the recovery marker, and
teleport-sized path discontinuities are excluded from distance features.

The classifier is a dependency-free nearest-task prototype over standardized,
interpretable movement, inventory-category, and block-action rates. Every fold
trains on two complete seed blocks and predicts the four sessions in the third.
No trajectory window from a held-out session enters training. Significance is
estimated with 10,000 label permutations performed independently within each
seed block. Chance accuracy is 25%. The five horizon tests use a Bonferroni
family-wise threshold of 0.01.

## Results

| Evidence available | Correct | Accuracy | Macro F1 | Permutation p |
| --- | ---: | ---: | ---: | ---: |
| 30 seconds | 5/12 | 0.417 | 0.333 | 0.1903 |
| 60 seconds | 9/12 | 0.750 | 0.760 | 0.0047 |
| 120 seconds | 10/12 | 0.833 | 0.833 | 0.0022 |
| 240 seconds | 10/12 | 0.833 | 0.804 | 0.0019 |
| 480 seconds | 8/12 | 0.667 | 0.667 | 0.0129 |

Thirty seconds did not distinguish tasks reliably. Held-seed performance rose
above chance by 60 seconds and peaked at 120–240 seconds. Full-session accuracy
fell to 8/12, showing that more elapsed behavior did not monotonically improve
separability. Explore was recognized in every seed block from 60 seconds onward;
most later confusion occurred among acquire, construct, and recover.
The 60-, 120-, and 240-second results pass the corrected threshold; the
full-session result does not.

## Interpretation boundary

This is positive evidence that these four protocol tasks leave distinguishable
behavioral traces across the three generated seed blocks for this participant.
It is not an identity classifier, a population result, or proof that the same
features transfer to another game, apparatus, participant, or task vocabulary.
The analysis was designed after collection and is therefore exploratory. A
future confirmatory test must freeze the feature set and classifier before any
new sessions are observed.

The complete aggregate confusion matrices are retained in
`experiments/labnote_001/task-inference.json`. Raw session streams and
session-level predictions are not embedded in this labnote.
