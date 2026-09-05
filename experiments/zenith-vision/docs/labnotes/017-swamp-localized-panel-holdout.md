# Labnote 017: swamp localized panel holdout

## Question

Does snowy-Hero successor candidate
`3d37e24ca4e8b57038724062fe87a370c98ec208d5bc0f1663aeb907e40b50f8`
generalize to a fresh balanced swamp holdout?

## Method

- Holdout: 16 newly captured, structurally masked swamp observations balanced
  across Inventory-only, Hero-only, Hero-plus-Inventory, and closed states.
- One segment was immediately corrected from Hero-plus-Inventory to Hero-only
  after the operator reported the staging mistake; correction occurred before
  transfer or evaluation.
- Holdout digest:
  `f1ad34543df11b60eaf3d92a610890cb0779ea9ad6d269d09d2d630c1a4a3fd6`.
- Threshold: candidate's frozen 0.65 threshold.
- Training and calibration: disabled.
- Gate: unchanged from Labnotes 012 and 015.
- Run: `89de33e6-63f8-4620-91cf-faa9c264002e`.

## Result

| State | Exact accuracy |
| --- | --- |
| Inventory only | 4/4 (100%) |
| Hero only | 0/4 (0%) |
| Hero + Inventory | 3/4 (75%) |
| Closed | 4/4 (100%) |

Aggregate exact accuracy was 11/16 (68.8%). Hero had 3 true positives, 8 true
negatives, 5 misses, and no false positives. Inventory had 8 true positives, 6
true negatives, 2 false positives, and no misses. The promotion gate failed.

The evaluator performed no training or calibration, emitted no sample-level
predictions, completed on CUDA in 3.6 seconds with exit code 0 and no stderr,
and released the accelerator lease normally.

## Decision

Reject the candidate and end the frozen-backbone localized-classifier branch.
Two distinct fresh holdouts exposed alternating environment-specific Hero
failures despite strong development cross-validation. Repeating the same loop
would spend operator labor and encourage sequential holdout overfitting.

Pivot to deterministic, inspectable GW2 UI evidence: exact window identity,
structural privacy masks, allowlisted title OCR, and stable panel chrome or icon
anchors. A visual classifier may provide secondary evidence only after a larger
independent corpus exists; it must not own the live decision.
