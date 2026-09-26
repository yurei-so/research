#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
set -euo pipefail

readonly ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
: "${VOXEL_GUIDANCE_DATA:?Deployment must supply the frozen dataset path}"
: "${VOXEL_GUIDANCE_PYTHON:?Deployment must supply the isolated Python interpreter}"
: "${ROOST_EXPERIMENT_ARTIFACT_DIR:?Scheduler must supply the private artifact directory}"

exec "$VOXEL_GUIDANCE_PYTHON" "$ROOT/run_training.py" \
  --data-root "$VOXEL_GUIDANCE_DATA" \
  --output "$ROOST_EXPERIMENT_ARTIFACT_DIR" \
  --epochs 20 \
  --batch-size 16 \
  --seed 1701 \
  --device cuda
