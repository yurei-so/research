# Labnote 013: varied Inventory position transfer

## Question

Does adding new Inventory-only development batches staged at left, right, and
center positions repair the localized candidate's position dependence?

## Method

- Private input: seven approved, structurally masked development batches.
- New data: three four-sample Inventory-only batches staged at left, right, and
  center positions.
- Spent holdout: excluded and not read.
- Model, regions, threshold, and development gate: unchanged from Labnote 011.
- Evaluation: seven leave-one-development-batch-out folds.
- Accelerator: RTX 4070 through the non-preemptive roostd experiment lease.
- Run: `17e8831a-d31a-4573-987e-8455e3c61693`.

## Result

| Held batch | Exact accuracy | Hero TP/FP/FN | Inventory TP/FP/FN |
| --- | --- | --- | --- |
| 001 | 9/9 (100%) | 7/0/0 | 2/0/0 |
| 002 | 4/9 (44.4%) | 3/0/4 | 2/0/1 |
| 003 | 12/12 (100%) | 8/0/0 | 7/0/0 |
| 004 | 12/12 (100%) | 0/0/0 | 8/0/0 |
| 005 left | 3/4 (75%) | 0/1/0 | 4/0/0 |
| 006 right | 4/4 (100%) | 0/0/0 | 4/0/0 |
| 007 center | 4/4 (100%) | 0/0/0 | 4/0/0 |

Aggregate exact accuracy was 48/54 (88.9%). Inventory generalized across all
three new position folds, but the second original environment collapsed through
four missed Hero states. The 44.4% fold violated the frozen 70% floor, so the
development gate failed and no candidate was emitted.

The job completed on CUDA with exit code 0 and no stderr. Agent Runtime and
roostd remained healthy with zero restarts, and the accelerator lease was
released normally.

## Decision

Do not package a successor candidate. The new data repaired the targeted
Inventory position behavior in development, but exposed order-sensitive Hero
head instability after the negative-class distribution changed.

Replace per-sample optimizer steps with a deterministic, class-balanced
full-batch multiple-instance objective. Re-run the same development-only folds
under the existing gate. Do not read or rerun the spent holdout.
