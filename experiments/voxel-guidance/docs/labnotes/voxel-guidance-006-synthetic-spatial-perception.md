---
schema_version: 1
id: voxel-guidance-006
title: "Temporal synthetic spatial-perception calibration"
date: 2026-09-25
status: complete
outcome: mixed
question: "Do short grayscale frame sequences plus ego-motion improve local spatial estimates over a matched single-frame baseline on held-out procedural geometry?"
tags: ["synthetic-data","spatial-ai","temporal-vision","blender","apparatus"]
lineage: ["voxel-guidance-005"]
relations: [{"target":"voxel-guidance-005","type":"extends","rationale":"Moves from compact behavioral state interpretation to a separately bounded test of compact machine-facing spatial state."}]
publish: true
---
# Labnote 006: Temporal synthetic spatial-perception calibration

## Question

Can a compact temporal model infer useful local spatial state from four
low-resolution grayscale observations plus ego-motion, and does it outperform
a parameter-matched model that sees only the final frame?

## Method

Blender 5.2.2 generated 384 deterministic four-frame sequences: 256 train, 64
validation, and 64 held-out test scenes with disjoint seed ranges. Each frame
contained a 64 by 64 grayscale observation, an exact 16 by 16 ray-cast depth
target, a depth-discontinuity mask, and ego-motion. File digests, tensor
shapes, label derivation, and the complete split manifest were validated and
frozen before training.

The matched 171,682-parameter conditions used the same encoder, ConvGRU, and
prediction heads. The single-frame condition received only the final frame;
the temporal condition received all four observations and ego-motion. Both
trained for 20 epochs with seed 1701 on an RTX 4070. The test split was
evaluated once after both runs finished.

## Results

| Condition | Depth MAE, m | Free-space IoU | Discontinuity F1 |
| --- | ---: | ---: | ---: |
| Single frame | 1.9242 | 0.8592 | 0.7531 |
| Temporal ConvGRU | 1.8467 | 0.8385 | 0.7818 |
| Temporal minus single | -0.0776 | -0.0207 | +0.0287 |

The temporal condition modestly improved depth error and discontinuity
detection while modestly worsening free-space overlap. The run completed with
exit code zero and empty stderr. The frozen result and scheduler receipt
are retained under `experiments/labnote_006/`.

## Interpretation

This is a mixed result. Short temporal context was useful for two of the three
precommitted spatial metrics, but did not dominate the single-frame baseline.
The result supports continuing to a separately frozen transfer probe rather
than treating temporal memory as an unconditional improvement.

## Intended boundary

The experiment predicts local depth, free space, and depth discontinuities on
held-out procedural geometry. It does not establish complete mesh
reconstruction, general game understanding, navigation competence, or transfer
to real game imagery. A cross-game probe requires a later frozen protocol.
