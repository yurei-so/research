# Labnote 012: localized panel frozen holdout

## Question

Does the localized panel candidate that passed development cross-validation
generalize to a separately frozen, balanced live Small-UI holdout?

## Method

- Candidate: content-addressed localized model
  `256bc9c9d71497b174ba57210b2e8fc76443f6981223136f2d6a81daec3f1926`.
- Holdout: 16 newly captured, structurally masked observations balanced across
  Inventory-only, Hero-plus-Inventory, Hero-only, and closed-panel states.
- Labels: bound from operator-staged states before transfer; recognition did
  not run during capture.
- Holdout digest:
  `76a5cf1552eb06a2265b16e10ea1f039bb80b30cc2a7ea760291b3ad41419363`.
- Threshold: candidate's frozen 0.65 threshold.
- Training and calibration: disabled.
- Promotion gate, fixed before evaluation: at least 87.5% aggregate exact
  accuracy, at least 75% exact accuracy in every state, and no class above a
  12.5% aggregate false-call-plus-miss rate.
- Accelerator: RTX 4070 through the non-preemptive roostd experiment lease.
- Run: `2ed92d59-2e2b-4270-8856-8f1f4843f316`.

## Result

| State | Exact accuracy |
| --- | --- |
| Inventory only | 0/4 (0%) |
| Hero + Inventory | 4/4 (100%) |
| Hero only | 4/4 (100%) |
| Closed | 4/4 (100%) |

Aggregate exact accuracy was 12/16 (75%). Hero was perfect with 8 true
positives, 8 true negatives, no false positives, and no misses. Inventory had
4 true positives, 8 true negatives, no false positives, and 4 misses. Its 25%
aggregate error rate exceeded the frozen 12.5% ceiling. The promotion gate
failed.

The evaluator performed no training or calibration, emitted no sample-level
predictions, completed on CUDA in 3.6 seconds with exit code 0 and no stderr,
and released the accelerator lease normally.

## Decision

Reject the candidate for live use. The holdout is spent and must not be used
for threshold selection, region changes, training, or repeat evaluation.

The aggregate pattern suggests that Inventory evidence remains coupled to the
panel arrangement seen when Hero is also open. Treat that as a direction for
new development data, not as permission to inspect or fit this holdout. Collect
new development-only Inventory observations with independently varied panel
positions, environments, and combat conditions. Any successor architecture
must pass a newly frozen development gate and a different fresh holdout.
