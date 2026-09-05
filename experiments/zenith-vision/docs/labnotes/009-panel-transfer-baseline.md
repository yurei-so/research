# Labnote 009: panel transfer baseline

## Question

Does a frozen ImageNet-pretrained MobileNet V3 Small backbone provide enough
visual structure to recognize Hero and Inventory across development batches
without spending another holdout?

## Method

- Private input: three approved, structurally masked development batches only.
- Spent holdout: not transferred to mpai and not read by the experiment.
- Model: pretrained MobileNet V3 Small with frozen backbone; classifier head only.
- Augmentation: bounded translation, scale, brightness, contrast, and saturation.
- Evaluation: three leave-one-batch-out folds.
- Accelerator: RTX 4070 through the non-preemptive roostd experiment lease.
- Run: `f2cdd2d9-7476-4f2d-96b3-dc56283329d0`.

## Result

| Held batch | Exact accuracy | Hero TP/FP/FN | Inventory TP/FP/FN |
| --- | --- | --- | --- |
| 001 | 7/9 (77.8%) | 7/0/0 | 2/2/0 |
| 002 | 6/9 (66.7%) | 7/1/0 | 1/0/2 |
| 003 | 8/12 (66.7%) | 8/4/0 | 7/0/0 |

The job completed on CUDA with exit code 0 and no stderr. The accelerator lease
was released normally.

## Decision

Do not freeze a new holdout or promote the model. Transfer learning materially
improved over the rejected 33.3% global-feature holdout result, but generalization
remains insufficient. Hero recall is complete while false positives increase in
the bright third environment; Inventory performance varies by placement and
batch.

Collect corrective development data emphasizing diverse no-Hero scenes,
Inventory-only positions, and closed-panel negatives. Re-run development-only
cross-batch evaluation before spending a new holdout.
