---
schema_version: 1
id: voxel-guidance-005
title: "Semantic namespace token ablation"
date: 2026-09-10
status: complete
outcome: negative
question: "Can a semantic namespace token replace the full field dictionary when a local model interprets compact behavioral state?"
tags: ["behavioral-telemetry","machine-native-state","namespace","ablation","local-model","negative-result"]
lineage: ["voxel-guidance-004"]
relations: [{"target":"voxel-guidance-004","type":"motivated-by","rationale":"Labnote 004 found that the shared field dictionary dominated compact prompt cost, so this note tested whether one semantic namespace could replace it."}]
publish: true
---
# Labnote 005: Semantic namespace token ablation

## Question

Can a human-readable namespace such as
`[ns:voxel-guidance.behavior-window.v1]` give a local model enough conceptual
context to interpret abbreviated machine-state fields without the full field
dictionary?

## Method

This exploratory ablation reused the 12 accepted `pilot-v2` behavior windows
at 120 seconds and the `qwen3:8b` artifact from Labnote 004. The model, digest,
task definitions, structured four-label output, temperature zero, seed 1701,
and thinking-disabled setting remained fixed. Four compact representations were
compared:

1. the complete field-ID dictionary and no semantic namespace;
2. a semantic namespace and no dictionary;
3. a semantic namespace plus a shorter feature-group grammar; and
4. an opaque schema digest with neither namespace nor dictionary.

The final block ran every variant twice. Only aggregate confusion matrices,
prompt-token counts, timings, and repeat checks were retained. The variants
were designed after Labnote 004 and are not confirmatory tests.

## Results

| Variant | Correct | Accuracy | Mean prompt tokens |
| --- | ---: | ---: | ---: |
| Full field dictionary | 7/12 | 0.583 | 579.667 |
| Semantic namespace only | 3/12 | 0.250 | 378.667 |
| Namespace + group grammar | 1/12 | 0.083 | 432.667 |
| Opaque schema only | 3/12 | 0.250 | 366.667 |

Namespace-only and opaque-schema control produced exactly the same 12
predictions. The semantic namespace therefore supplied no measurable zero-shot
benefit in this run while adding about 12 prompt tokens. The short group grammar
did not preserve the full dictionary's semantics and performed worse. Removing
the dictionary reduced the prompt by 34.68% relative to the full-dictionary
condition, but also removed its numerical task-recognition advantage.

Both repeats retained the same accuracy for every variant. The three reduced-
context variants retained identical aggregate confusion matrices; the full
dictionary changed its confusion matrix while remaining 7/12, reinforcing the
known backend nondeterminism boundary.

## Interpretation boundary

The proposed namespace token did **not** replace explicit field semantics for
this model and task. A namespace may still be operationally valuable for schema
routing, validation, caching, or systems that have learned its meaning through
training or repeated context. This result only rejects the stronger zero-shot
idea that a readable namespace header by itself would let this model recover
the abbreviations' meaning.

The full dictionary's 7/12 result is exploratory rather than a validated model
score: the sample is small, reused, single-model, and post hoc, and its detailed
confusion pattern was not perfectly repeatable. Aggregate results are retained
at `experiments/labnote_001/namespace-ablation.json`.
