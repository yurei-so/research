# Labnote 001: default-layout geometry on a real holdout

## Question

Can the deterministic default-layout proposal serve as a UI-region detector,
or is it only suitable for conservative crop routing?

## Method

One operator-approved, structurally masked 1920x1080 Guild Wars 2 frame was
admitted as a private, non-release test holdout. The operator separately
approved tight boxes for three visible regions: objectives, skill bar, and
minimap. Chat and party/squad panels remained masked and unlabeled.

The checked-in default-layout proposals were compared with these verified boxes
using kind-matched intersection-over-union. No private pixels, recognized text,
character names, or paths are recorded here.

## Result

| Metric | Result |
| --- | ---: |
| Verified regions | 3 |
| Proposals | 5 |
| Mean IoU | 0.418298 |
| Recall at IoU 0.50 | 0.000000 |

The default geometry matched zero of three verified regions at the preexisting
0.50 threshold.

## Decision

The deterministic geometry remains a low-confidence crop heuristic. It is
rejected as detector ground truth and must not issue semantic observations or
privacy reveal decisions.

One frame is not enough to select or train a learned detector. The next gate is
a small, varied, separately consented real holdout collected under the same
structural masking policy. Model dependencies remain deferred until that corpus
demonstrates sufficient layout variation and reviewed labels.
