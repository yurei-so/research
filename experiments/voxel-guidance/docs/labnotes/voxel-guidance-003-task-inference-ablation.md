---
schema_version: 1
id: voxel-guidance-003
title: "Current-task feature-family ablation"
date: 2026-09-10
status: complete
outcome: mixed
question: "Which observable behavior families carry the 120-second held-seed task-inference signal?"
tags: ["ablation","behavioral-telemetry","classification","minecraft","mixed-result"]
lineage: ["voxel-guidance-002"]
relations: [{"target":"voxel-guidance-002","type":"ablates","rationale":"Removes behavior feature families from the successful held-seed classifier to locate which observations carry its task signal."}]
publish: true
---
# Labnote 003: Current-task feature-family ablation

## Question

Which observable behavior families carry the 120-second held-seed task-
inference signal: movement, coarse inventory flow, or confirmed block actions?

## Method

This exploratory ablation reuses the 12 accepted `pilot-v2` sessions and the
same leave-one-seed-block-out nearest-prototype classifier as Labnote 002. The
120-second horizon was selected after the prefix analysis because it was the
earliest horizon with peak observed accuracy; it is not an independently
preregistered endpoint.

Seven feature projections were compared: all 25 features, each of the three
families alone, and the full set with each family removed. Every variant used
the same 10,000 within-block label permutations. These p-values compare each
variant with chance; they do not test a causal difference between variants.

## Results

| Feature projection | Features | Correct | Accuracy | Macro F1 | Permutation p |
| --- | ---: | ---: | ---: | ---: | ---: |
| All | 25 | 10/12 | 0.833 | 0.833 | 0.0015 |
| Block actions only | 8 | 10/12 | 0.833 | 0.833 | 0.0015 |
| Movement only | 7 | 9/12 | 0.750 | 0.760 | 0.0040 |
| Inventory only | 10 | 7/12 | 0.583 | 0.530 | 0.0742 |
| Without block actions | 17 | 9/12 | 0.750 | 0.743 | 0.0090 |
| Without inventory | 15 | 10/12 | 0.833 | 0.833 | 0.0015 |
| Without movement | 18 | 8/12 | 0.667 | 0.676 | 0.0200 |

Block actions alone reproduced the full model's predictions. Movement alone
retained a strong held-seed signal. Coarse inventory flow alone did not
reliably beat chance, and removing inventory did not change the full result.
Removing either block actions or movement reduced accuracy, although this
small descriptive ablation cannot establish that either decrement is a stable
causal effect.

## Interpretation boundary

At two minutes, task recognition appears to depend primarily on how the
participant changes the world, with route structure providing a second useful
view. The result is not explained by coarse inventory possession or churn.
Because the horizon and feature families were examined after collection, this
is hypothesis-generating evidence for a future frozen replication—not an
estimate of performance on new participants or arbitrary tasks.

Complete aggregate confusion matrices and method metadata are retained in
`experiments/labnote_001/task-ablation.json`. Session-level predictions and raw
streams are excluded from this labnote.
