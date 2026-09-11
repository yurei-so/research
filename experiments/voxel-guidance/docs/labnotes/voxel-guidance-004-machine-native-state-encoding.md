---
schema_version: 1
id: voxel-guidance-004
title: "Machine-native state serialization baseline"
date: 2026-09-10
status: complete
outcome: mixed
question: "Can two-minute behavior windows be represented compactly without loss, and does one local model preserve task recognition across prose, JSON, and typed tokens?"
tags: ["behavioral-telemetry","machine-native-state","serialization","apparatus","minecraft","local-model","mixed-result"]
lineage: ["voxel-guidance-003"]
publish: true
---
# Labnote 004: Machine-native state serialization baseline

## Question

Can the frozen two-minute Voxel Guidance behavior windows be represented as
compact typed machine state without losing numerical fidelity, what is the
representation cost, and does a first local-model probe preserve task
recognition across deterministic prose, canonical JSON, and typed tokens?

## Method

This apparatus validation reuses the same 25 aggregate behavioral features
from all 12 accepted `pilot-v2` sessions at the 120-second horizon. Each field
received a stable short identifier in a versioned schema. The same observation,
provenance, timestamp, and freshness lifetime were rendered as deterministic
natural-language prose, canonical minified JSON, and compact typed tokens such
as `[distpm:42.5]`.

JSON and compact representations were decoded and compared with the original
typed snapshots for exact equality. Raw streams, coordinates, world identity,
session identifiers, and serialized session-level observations are excluded
from the retained result. Sizes are UTF-8 bytes, not tokenizer-specific token
counts.

An exploratory downstream probe then gave all three representations to the
same locally hosted `qwen3:8b` artifact (digest prefix `500a1f06`) using one
constant field legend, task definitions, temperature zero, seed 1701, thinking
disabled, and a strict four-label structured-output contract. The final block
contained two repeats. This protocol was fixed before that block, but it was
designed after the transport result and is not a preregistered confirmation.

## Results

| Representation | Total bytes | Mean per snapshot | Median |
| --- | ---: | ---: | ---: |
| Deterministic prose | 13,556 | 1,129.667 | 1,132.5 |
| Canonical JSON | 5,852 | 487.667 | 490.5 |
| Compact typed tokens | 4,844 | 403.667 | 406.5 |

The compact representation was **64.27% smaller than deterministic prose** and
**17.22% smaller than canonical JSON**. JSON and compact decoding both retained
exact numerical equality across all 12 snapshots. The reference behavioral
classifier remained the previously measured 10/12 accuracy at this horizon;
this run does not reinterpret that task result.

### Exploratory local-model probe

| Representation | Correct | Accuracy | Mean prompt tokens | Pairwise agreement |
| --- | ---: | ---: | ---: | ---: |
| Deterministic prose | 3/12 | 0.250 | 656.667 | — |
| Canonical JSON | 2/12 | 0.167 | 584.667 | 7/12 vs prose |
| Compact typed tokens | 5/12 | 0.417 | 581.667 | 4/12 vs prose; 6/12 vs JSON |

The compact prompt used 11.42% fewer model-counted prompt tokens than prose but
only 0.51% fewer than JSON because the shared field legend dominated every
prompt. Both final repeats produced identical aggregate confusion matrices and
token counts. Separate apparatus preflight calls showed that fixed seed and
temperature zero did not always guarantee backend-level repeatability, so the
repeat result is not a general determinism guarantee.

## Interpretation boundary

The compact schema is a validated lossless transport for these bounded
observations. The compact representation's numerical lead over chance-level
prose and JSON is hypothesis-generating only: 12 reused sessions, one model,
one prompt, post hoc protocol design, correlated representations, and observed
backend nondeterminism do not establish a reasoning advantage. A confirmatory
comparison would need a frozen protocol, multiple model families or instances,
and repeated calls scored with paired statistics. Byte reduction also did not
translate directly into token reduction.

The reusable serializer belongs to `apparatus/state-encoding`; this labnote
records its first use by Voxel Guidance rather than making the format
Voxel-specific. Aggregate results are retained at
`experiments/labnote_001/state-encoding.json` and
`experiments/labnote_001/state-encoding-model.json`.
