#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
set -euo pipefail

readonly ROOT="/home/alu52/github/research/experiments/voxel-guidance/experiments/labnote_006"
readonly DATA="/home/alu52/.local/share/voxel-guidance-006/dataset"
readonly PYTHON="/home/alu52/.local/share/voxel-guidance-006/venv/bin/python"
: "${ROOST_EXPERIMENT_ARTIFACT_DIR:?Agent Runtime must supply the private artifact directory}"

exec "$PYTHON" "$ROOT/run_training.py" \
  --data-root "$DATA" \
  --output "$ROOST_EXPERIMENT_ARTIFACT_DIR" \
  --epochs 20 \
  --batch-size 16 \
  --seed 1701 \
  --device cuda
