# Labnote 008: first visual panel baseline

## Question

Can a compact CPU ridge classifier trained on masked Small-UI panel tiles
generalize from two development batches to a recognition-disabled frozen
holdout captured during a live world boss?

## Method

- Development set: 18 visually reviewed samples from batches 001 and 002.
- Frozen holdout: 12 samples collected with recognition disabled.
- Holdout composition: 2 closed, 2 Inventory-only, 3 Hero-only, and 5 with
  Hero plus Inventory.
- Input: overlapping left and center tiles after structural chat and party masks.
- Features: pooled luminance, horizontal/vertical gradients, local contrast,
  and luminance histograms.
- Model: independent regularized linear ridge outputs for Hero and Inventory.
- Decision threshold: 0.5, fixed before the holdout run.

## Result

| Metric | Result |
| --- | --- |
| Exact panel-set accuracy | 4/12 (33.3%) |
| Hero true positives | 7 |
| Hero false positives | 4 |
| Hero false negatives | 0 |
| Inventory true positives | 3 |
| Inventory false positives | 2 |
| Inventory false negatives | 4 |

## Decision

Reject the global pooled-image baseline. It captured Hero-like darkness and
world-boss scene structure rather than sufficiently local panel evidence, while
Inventory geometry varied too much for the small corpus. The frozen holdout is
spent and must never be reused for feature selection, threshold selection, or
model promotion.

Continue with localized structural evidence such as the Hero header/icon rail
and Inventory grid/header. Gather broader development data, then freeze a new
holdout before the next evaluation.
