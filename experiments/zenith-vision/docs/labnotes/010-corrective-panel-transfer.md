# Labnote 010: corrective panel transfer

## Question

Does adding an approved Inventory-only and closed-panel development batch fix
the cross-batch false-positive behavior of the frozen MobileNet V3 Small panel
classifier without spending a fresh holdout?

## Method

- Private input: four approved, structurally masked development batches only.
- Corrective batch: 12 Small-UI observations containing eight Inventory-only
  states and four closed-panel negatives.
- Spent and future holdouts: not transferred to mpai and not read by the
  experiment.
- Model: ImageNet-pretrained MobileNet V3 Small with frozen backbone;
  classifier head only.
- Augmentation: bounded translation, scale, brightness, contrast, and
  saturation.
- Evaluation: four leave-one-batch-out folds, 18 epochs per fold.
- Accelerator: RTX 4070 through the non-preemptive roostd experiment lease.
- Run: `ced33ac9-6ad6-4e8c-afc3-109f989d4045`.

## Result

| Held batch | Exact accuracy | Hero TP/FP/FN | Inventory TP/FP/FN |
| --- | --- | --- | --- |
| 001 | 5/9 (55.6%) | 7/0/0 | 2/4/0 |
| 002 | 7/9 (77.8%) | 7/0/0 | 2/1/1 |
| 003 | 9/12 (75.0%) | 7/1/1 | 7/1/0 |
| 004 corrective | 8/12 (66.7%) | 0/4/0 | 6/0/2 |

Aggregate exact accuracy was 29/42 (69.0%). The job completed on CUDA with
exit code 0 and no stderr. Agent Runtime and roostd remained healthy with zero
restarts, and the accelerator lease was released normally.

## Decision

Reject this corrective model and do not spend a fresh holdout. The new batch
exposed rather than repaired cross-environment confounding: the model produced
four false Hero detections in a batch containing no Hero examples, missed two
Inventory states there, and regressed to four false Inventory detections on the
first batch. No fold reached 80% exact accuracy.

Do not respond with more epochs or another blind classifier-head run on the
same corpus. The next development slice should separate panel evidence into
localized regions, add visually diverse negatives for each class, and freeze a
development-only calibration gate before any new holdout is collected or read.
