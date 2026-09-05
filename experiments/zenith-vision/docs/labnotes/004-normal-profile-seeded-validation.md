# Labnote 004: frozen Normal profile seeded validation

## Question

Does the frozen Normal UI crop profile remain visually acceptable across a
fresh, independently collected gameplay batch?

## Method

- Profile was frozen before validation collection.
- Dataset: `operator-normal-validation-v1`
- 12 distinct, private, test-only 1920x1080 gameplay frames
- 36 reviewed regions: objectives, skill bar, and minimap
- Exact game-window selection and the Normal structural privacy mask were
  revalidated during collection.
- The operator separately approved the privacy sheet and frozen-profile overlay.
- Private images and text are not reproduced here.

The review was seeded with the frozen profile boxes. The operator could reject
the overlay, but did not draw independent boxes. This limits what the result can
claim.

## Result

| Metric | Result |
| --- | ---: |
| Frames | 12 |
| Reviewed labels | 36 |
| Mean IoU | 1.000000 |
| Recall at IoU 0.50 | 36/36 (1.000000) |

Every objectives, skill-bar, and minimap proposal was accepted unchanged.

## Interpretation

The frozen Normal crop profile is stable across the newly collected scenes and
the full capture, privacy review, admission, annotation review, and evaluation
chain works end to end. The perfect score is expected because accepted seeded
boxes become the reviewed labels. It is not independent localization evidence
and must not be reported as detector accuracy.

## Decision

- Retain the frozen Normal profile as an operator-reviewed crop heuristic.
- Do not promote it to semantic detector status.
- Do not spend more operator time on repeated seeded validation batches.
- Build a private freehand or blind annotation mode before claiming independent
  geometric accuracy or deciding whether learned localization is warranted.
- Small and Large remain frozen but unvalidated by an independent annotation
  process. Larger/XL remains unsupported.
