# Labnote 003: UI-scale stratification

## Question

Does one generic default-layout geometry describe the visible Guild Wars 2 HUD
across the Small, Normal, and Large UI profiles?

## Data and review

Three private, test-only operator holdouts were evaluated:

| UI profile | Frames | Labels |
| --- | ---: | ---: |
| Small | 12 | 36 |
| Normal | 12 | 36 |
| Large | 12 | 36 |

Each frame contains operator-approved objectives, skill-bar, and minimap boxes.
Collection was window-bound, structurally masked, deduplicated, and separately
approved for privacy and annotation. Private image and text content are not
recorded here. Larger/XL was deliberately excluded by operator decision.

## Generic baseline result

| UI profile | Mean IoU | Recall at IoU 0.50 |
| --- | ---: | ---: |
| Small | 0.418298 | 0/36 (0.000000) |
| Normal | 0.533216 | 24/36 (0.666667) |
| Large | 0.607690 | 24/36 (0.666667) |

Per-region recall:

| UI profile | Objectives | Skill bar | Minimap |
| --- | ---: | ---: | ---: |
| Small | 0/12 | 0/12 | 0/12 |
| Normal | 0/12 | 12/12 | 12/12 |
| Large | 0/12 | 12/12 | 12/12 |

## Interpretation

UI scale is a material layout variable. The generic geometry happens to align
best with Large and moderately with Normal, but fails Small entirely. Its
objectives proposal fails every reviewed profile, so aggregate success on two
regions must not be treated as detector validity.

The current reviewed boxes were generated as profile-specific seeds and then
approved by the operator. They can define frozen crop-profile candidates, but
evaluating those candidates on the same frames would be circular. Independent
post-freeze validation is required.

## Decision

- Reject a single scale-agnostic geometry profile.
- Preserve explicit Small, Normal, and Large strata.
- Keep Larger/XL unsupported and do not infer it from Large.
- Freeze profile-specific crop candidates next.
- Evaluate each frozen profile on newly collected, separately reviewed frames
  before promotion.
- Continue treating all geometry as crop heuristics, not semantic detection.
