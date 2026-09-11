# Research apparatus

Reusable local tools for human review, annotation, scoring, evaluation, and
experiment operation live here. Apparatus must retain the privacy and authority
boundaries of the experiments it supports.

- `mujoco-lab/` provides pinned deterministic physics scenes and Blender replay
  exports for multiple experiment families. It is apparatus, not a research
  result or a new experiment family.
- `state-encoding/` provides versioned schemas and deterministic prose, JSON,
  and compact typed-token views of the same bounded machine observations. It
  measures representation cost and fidelity; reasoning effects belong to the
  consuming experiment.
