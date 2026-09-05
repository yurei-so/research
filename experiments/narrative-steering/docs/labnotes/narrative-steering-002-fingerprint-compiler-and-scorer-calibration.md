---
schema_version: 1
id: narrative-steering-002
title: "Fingerprint compiler and blinded scorer calibration"
date: 2026-09-05
status: complete
outcome: mixed
question: "Which pilot steering coordinates are stable across story states, and can a blinded local model scorer reproduce the human measurements well enough to reduce future review burden?"
tags: ["blinded-review","human-review","mixed-result","model-comparison","narrative-steering","story-engine"]
lineage: ["narrative-steering-001"]
publish: true
---
# Labnote 002: Fingerprint compiler and blinded scorer calibration

## Question

Which pilot steering coordinates are stable across story states, and can a
blinded local model scorer reproduce the human measurements well enough to
reduce future review burden?

## Method

The compiler treats each story state, rather than each continuation, as the
bootstrap unit. For every model and coordinate it records the neutral raw mean,
matched-state-relative mean, 95% state-bootstrap interval, per-state direction,
leave-one-state-out range, and agency-guard shift. This prevents repeated
samples from masquerading as independent narrative contexts.

An independent local `deepseek-r1:8b` scorer then evaluated the 48-item blinded
bundle without model identities or human judgments. Each dimension was
calibrated with leave-one-story-state-out bias correction. A dimension was
eligible for assisted expansion only when corrected MAE was at most `0.75`, at
least 80% of predictions were within one scale point, and nonzero sign
agreement was at least 70%.

## Compiled candidate fingerprint

The strongest state-bootstrap-relative coordinates were:

| Model | Coordinate | Mean | 95% state-bootstrap interval | Same-direction states |
| --- | --- | ---: | ---: | ---: |
| Qwen 3 8B | agency | +0.917 | [+0.500, +1.375] | 4/4 |
| Qwen 3 8B | social | -0.458 | [-0.958, -0.083] | 4/4 |
| Gemma 3 12B | agency | -0.458 | [-0.750, -0.125] | 4/4 |
| Gemma 3 12B | intimacy | -0.250 | [-0.333, -0.167] | 4/4 |
| Llama 3.2 3B | agency | -0.458 | [-0.750, -0.125] | 4/4 |
| Llama 3.2 3B | causal fortune | +0.500 | [+0.167, +0.750] | 3/4 |
| Llama 3.2 3B | closure | -0.292 | [-0.417, -0.167] | 4/4 |

These are model-relative pilot coordinates. Negative relative agency for Gemma
and Llama does not independently mean severe agency violation; both had the
same neutral raw mean (`-0.375`) while Qwen's raw mean was `+1.000`.

## Automated scorer calibration

| Coordinate | Corrected MAE | Within one | Sign agreement | Eligible |
| --- | ---: | ---: | ---: | --- |
| agency | 1.014 | 56.3% | 42.9% | no |
| affect | 0.826 | 66.7% | 58.6% | no |
| social | 0.914 | 62.5% | 58.3% | no |
| causal fortune | 0.872 | 66.7% | 78.9% | no |
| closure | 1.024 | 62.5% | 60.0% | no |
| escalation | 1.186 | 43.8% | 63.2% | no |
| intimacy | 0.571 | 89.6% | 85.0% | yes |

The scorer is authorized only as a candidate intimacy instrument. In
particular, it must not score or select agency cases autonomously. This is a
useful negative calibration result: naïve automated scoring would have damaged
the experiment's strongest human-observed signal.

## Decision

Preserve the compiled human fingerprint as version 1. The next replication
should target the stable coordinates and obtain a small independent human or
agent review sample. Automated scoring may reduce burden for intimacy, but the
remaining dimensions require either a better calibrated scorer or deliberately
small human adjudication sets. Cone visualization remains out of scope.
