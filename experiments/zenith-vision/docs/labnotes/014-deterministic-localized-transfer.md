# Labnote 014: deterministic localized transfer

## Question

Does deterministic, class-balanced full-batch multiple-instance training retain
Hero generalization after adding varied Inventory-only position data?

## Method

- Private input: the same seven approved, structurally masked development
  batches used by Labnote 013.
- Spent holdout: excluded and not read.
- Regions, backbone, threshold, and development gate: unchanged.
- Training change: replace order-sensitive per-sample optimizer steps with a
  normalized smooth-maximum, class-balanced full-batch objective.
- Evaluation: seven leave-one-development-batch-out folds.
- Accelerator: RTX 4070 through the non-preemptive roostd experiment lease.
- Run: `fbb1b860-f50b-4d16-8ca1-4a388e4ec8ab`.

## Result

| Held batch | Exact accuracy | Hero TP/FP/FN | Inventory TP/FP/FN |
| --- | --- | --- | --- |
| 001 | 9/9 (100%) | 7/0/0 | 2/0/0 |
| 002 | 7/9 (77.8%) | 6/0/1 | 2/0/1 |
| 003 | 11/12 (91.7%) | 8/1/0 | 7/0/0 |
| 004 | 12/12 (100%) | 0/0/0 | 8/0/0 |
| 005 left | 3/4 (75%) | 0/1/0 | 4/0/0 |
| 006 right | 4/4 (100%) | 0/0/0 | 4/0/0 |
| 007 center | 4/4 (100%) | 0/0/0 | 4/0/0 |

Aggregate exact accuracy was 50/54 (92.6%). Hero's aggregate error rate was
5.6%; Inventory's was 1.9%. The previously collapsing second fold improved from
44.4% to 77.8%, and all three new position folds retained complete Inventory
recall. The frozen development gate passed.

The gate emitted content-addressed candidate
`bc155807a28aee1a2d7d10fb18a96b24d40b9fe300fc3e01650f70e5d61cc649`,
bound to development corpus
`303b996aa1791eeb5f151bcc85a4df571046d9fec17e640b83955bdcf0f34796`.
The job completed on CUDA with exit code 0 and no stderr, and roostd released
the accelerator lease normally.

## Decision

Accept the deterministic architecture as a successor candidate eligible for a
different fresh holdout. Do not promote it to live use, and do not evaluate it
against the spent Labnote 012 holdout.

Retire the registered Labnote 012 evaluator so an operator cannot accidentally
rerun the spent holdout. A future holdout must receive a new digest-bound
definition and explicit scientific record.
