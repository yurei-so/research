# Labnote 015: snowy localized panel holdout

## Question

Does deterministic localized candidate
`bc155807a28aee1a2d7d10fb18a96b24d40b9fe300fc3e01650f70e5d61cc649`
generalize to a fresh balanced holdout captured during the snowy Claw of
Jormag encounter?

## Method

- Holdout: 16 newly captured, structurally masked observations balanced across
  Inventory-only, Hero-plus-Inventory, Hero-only, and closed-panel states.
- Labels: bound from operator-staged states before transfer; recognition did
  not run during capture.
- Holdout digest:
  `dbb09c405d8da0492a44f8755ff6bebbc349128191a235f4e4d25790171257a1`.
- Threshold: candidate's frozen 0.65 threshold.
- Training and calibration: disabled.
- Gate: at least 87.5% aggregate exact accuracy, at least 75% exact accuracy in
  every state, and no class above a 12.5% aggregate error rate.
- Accelerator: RTX 4070 through the non-preemptive roostd experiment lease.
- Run: `493e5c21-aa9a-4957-a843-11dffd555aa2`.

## Result

| State | Exact accuracy |
| --- | --- |
| Inventory only | 4/4 (100%) |
| Hero + Inventory | 4/4 (100%) |
| Hero only | 2/4 (50%) |
| Closed | 4/4 (100%) |

Aggregate exact accuracy was 14/16 (87.5%). Inventory classification was
perfect with 8 true positives, 8 true negatives, and no errors. Hero had 6 true
positives, 8 true negatives, 2 misses, and no false positives. Its 12.5% class
error rate met the ceiling, but the 50% Hero-only state accuracy failed the
frozen 75% state floor. The promotion gate therefore failed.

The evaluator performed no training or calibration, emitted no sample-level
predictions, completed on CUDA in 3.6 seconds with exit code 0 and no stderr,
and released the accelerator lease normally.

## Decision

Do not promote the candidate. The snowy holdout is spent and must not be used
for tuning or repeat evaluation.

Inventory position generalization is now supported by fresh evidence. The next
development direction is Hero-only evidence across independently collected
bright and snowy environments. Any successor must pass the development gate
and a different fresh holdout.
