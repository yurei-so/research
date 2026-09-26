# Voxel Guidance 006 — synthetic spatial perception

This directory contains the frozen apparatus for an approval-gated comparison of
single-frame and temporal local spatial perception from deliberately poor
grayscale observations. Blender owns synthetic observation and ray-cast label
generation. The training process never invokes Blender and receives only
manifest-bound dataset shards.

Calibration outputs are disposable and are not scientific evidence. The
protocol was frozen only after deterministic replay, projection alignment,
split isolation, and a bounded CUDA smoke train passed.

```bash
BLENDER=/path/to/blender
"$BLENDER" --background --python generate_dataset.py -- \
  --output /path/to/calibration --split calibration --seed-start 9000 --sequences 8

python validate_dataset.py /path/to/calibration/manifest.json
```

The production dataset is additionally bound by `dataset-manifest.json`; its
receipt is recorded in `frozen-protocol.json` and verified again by the
training entrypoint.

`run_training.py` validates every shard digest before importing PyTorch. Its
output directory is supplied by the approval-gated scheduler through
`ROOST_EXPERIMENT_ARTIFACT_DIR`; deployment-specific interpreter and dataset
paths are supplied through explicit environment variables.

No raw game captures, personal worlds, identifiers, or coordinates belong in
this apparatus. Cross-game observations require a later frozen transfer
protocol.
