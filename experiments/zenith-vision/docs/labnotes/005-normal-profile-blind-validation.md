# Labnote 005: Normal profile blind human validation

## Question

Does the frozen Normal UI crop profile agree with independently drawn human
boxes on fresh gameplay frames?

## Method

- Three representative frames were selected from the fresh private Normal
  validation batch before annotation.
- Each privacy-redacted frame was opened in Krita without suggested geometry.
- The operator independently drew filled rectangles on separate objectives,
  skill-bar, and minimap layers.
- The bridge extracted only normalized alpha bounds after save.
- It rejected missing, empty, fragmented, or ambiguous layer masks.
- Nine independent labels were compared with the already-frozen Normal profile.
- Private images and text are not reproduced here.

## Result

| Region | Labels | Matched at IoU 0.50 | Mean IoU |
| --- | ---: | ---: | ---: |
| Objectives | 3 | 3 | 0.731710 |
| Skill bar | 3 | 3 | 0.655322 |
| Minimap | 3 | 3 | 0.857187 |
| **Overall** | **9** | **9** | **0.748073** |

Overall recall at IoU 0.50 was `1.000000`.

## Interpretation

Unlike seeded overlay approval, this result provides independent geometric
evidence. The frozen Normal profile is suitable as a practical crop heuristic
for these three HUD regions at 1920x1080.

The minimap is most stable. The objectives panel varies in height with visible
content, while the skill-bar crop is deliberately broader than the independent
human boxes. Both still clear the precommitted IoU threshold in all three
samples.

The sample is small and supports crop selection, not semantic detection or
cross-resolution generalization.

## Decision

- Promote the frozen Normal geometry from provisional to independently
  validated crop heuristic at 1920x1080.
- Retain objectives as a conservative maximum-height crop; consider
  content-adaptive trimming later.
- Do not train a detector solely to replace this profile.
- Reuse the blind Krita bridge for Small or Large only when those profiles need
  promotion.
- Larger/XL remains unsupported.
