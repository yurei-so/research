# Labnote 002: batch holdout geometry confirmation

## Question

Does the default-layout geometry baseline recover operator-reviewed visible HUD
regions across a larger private gameplay holdout?

## Data and review

- Dataset: `operator-holdout-v1`
- 12 distinct, privacy-reviewed gameplay frames
- Test-only, private, not for release
- 3 operator-approved regions per frame: objectives, skill bar, and minimap
- 36 total labels
- Raw gameplay content and text are not recorded in this labnote

The collector revalidated the exact game-window identity for every frame,
structurally masked chat and party/squad areas, rejected near-duplicates, and
discarded raw captures. The operator separately approved the privacy contact
sheet and the annotation overlay contact sheet before labels were locked.

## Result

| Metric | Result |
| --- | ---: |
| Frames | 12 |
| Reviewed labels | 36 |
| Mean IoU | 0.418298 |
| Recall at IoU 0.50 | 0.000000 (0/36) |

## Interpretation

The result exactly reproduces Labnote 001 because the reviewed HUD geometry is
stable across this batch. The expanded batch varies scene content, not UI
layout, resolution, scale, or configuration. It therefore confirms that the
existing default boxes are useful conservative crop heuristics but do not meet
the detector threshold.

This is not yet an adequate detector-training corpus: repeating identical box
geometry across additional frames adds visual backgrounds but little geometric
supervision. A learned detector should not be started from this result alone.

## Decision

- Retain the current geometry as low-confidence crop proposals.
- Reject promotion to semantic detector status.
- Preserve the 12-frame set as a private regression holdout.
- Before training, collect bounded reviewed strata that vary resolution, UI
  scale, objective-panel height/state, minimap configuration, and skill-bar
  state. Keep those future samples outside this holdout.
