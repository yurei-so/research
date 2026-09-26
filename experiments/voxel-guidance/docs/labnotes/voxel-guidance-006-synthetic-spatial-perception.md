---
schema_version: 1
id: voxel-guidance-006
title: "Temporal synthetic spatial-perception calibration"
date: 2026-09-25
status: running
outcome: pending
question: "Do short grayscale frame sequences plus ego-motion improve local spatial estimates over a matched single-frame baseline on held-out procedural geometry?"
tags: ["synthetic-data","spatial-ai","temporal-vision","blender","apparatus"]
lineage: ["voxel-guidance-005"]
relations: [{"target":"voxel-guidance-005","type":"extends","rationale":"Moves from compact behavioral state interpretation to a separately bounded test of compact machine-facing spatial state."}]
publish: false
---
# Labnote 006: Temporal synthetic spatial-perception calibration

## Question

Can a compact temporal model infer useful local spatial state from four
low-resolution grayscale observations plus ego-motion, and does it outperform
a parameter-matched model that sees only the final frame?

## Current status

The apparatus passed deterministic generation, label validation, split
isolation, and CUDA smoke training. The protocol and 384-sequence dataset are
now frozen. The approval-gated evidentiary run is pending; no outcome is
claimed yet. The protocol, Blender generator, dataset validator, model code,
and bounded mpai runner live under `experiments/labnote_006/`.

## Intended boundary

The experiment predicts local depth, free space, and depth discontinuities. It
does not claim complete mesh reconstruction, general game understanding,
navigation competence, or transfer to real game imagery. A cross-game probe
requires a later frozen protocol and may not be added after seeing this test
result.
