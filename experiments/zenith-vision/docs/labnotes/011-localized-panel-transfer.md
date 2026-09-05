# Labnote 011: localized panel transfer

## Question

Can class-specific localized evidence avoid the environmental confounding seen
by whole-tile transfer learning while preserving development-only evaluation?

## Method

- Private input: four approved, structurally masked development batches only.
- Spent and future holdouts: not transferred to mpai and not read.
- Evidence plan: ten Hero header/icon-rail proposals and eight Inventory-grid
  proposals across the overlapping left and center tiles.
- Backbone: ImageNet-pretrained MobileNet V3 Small, frozen.
- Heads: independent multiple-instance linear classifiers trained from
  sample-level labels; one matching localized region is sufficient evidence.
- Threshold: 0.65, fixed before evaluation.
- Evaluation: four leave-one-development-batch-out folds.
- Promotion gate, fixed before evaluation: at least 80% aggregate exact
  accuracy, at least 70% exact accuracy in every fold, and no class above a
  20% aggregate false-call-plus-miss rate.
- Accelerator: RTX 4070 through the non-preemptive roostd experiment lease.
- Run: `e00f5b3b-7afe-45e5-9bf2-07436241061c`.

## Result

| Held batch | Exact accuracy | Hero TP/FP/FN | Inventory TP/FP/FN |
| --- | --- | --- | --- |
| 001 | 9/9 (100%) | 7/0/0 | 2/0/0 |
| 002 | 8/9 (88.9%) | 7/0/0 | 2/0/1 |
| 003 | 10/12 (83.3%) | 8/2/0 | 7/0/0 |
| 004 corrective | 12/12 (100%) | 0/0/0 | 8/0/0 |

Aggregate exact accuracy was 39/42 (92.9%). Hero's aggregate error rate was
4.8%; Inventory's was 2.4%. The frozen development gate passed. The job
completed on CUDA in 35.6 seconds with exit code 0 and no stderr. Agent Runtime
and roostd remained healthy with zero restarts, and the accelerator lease was
released normally.

## Decision

Accept localized panel evidence as the first candidate architecture to earn a
fresh holdout. This does not promote a production model: the same small corpus
still supplied both training batches and cross-batch evaluation environments.

Before reading new holdout pixels, train and durably package one final model
from all approved development batches with the region plan, threshold, model
metadata, and corpus digests bound together. Then collect a separately frozen,
recognition-disabled live set with intentional Hero, Inventory, combined, and
closed-panel state variety. Keep the operator's current ordinary gameplay out
of the holdout unless it is explicitly admitted through that collection flow.
