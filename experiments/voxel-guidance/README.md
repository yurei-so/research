# Voxel Guidance Research

This experiment family asks whether bounded Minecraft play can produce a
repeatable, interpretable behavioral vector. The goal is to measure patterns
within a deliberately designed task battery—not to infer identity,
personality, diagnosis, intent, or behavior outside the experiment.

## System boundary

- [`yurei-so/prism-toolkit`](https://github.com/yurei-so/prism-toolkit) owns
  launcher discovery, creation, and launch authority.
- A lightweight Fabric bridge will emit the narrow event vocabulary defined by
  the frozen protocol.
- This repository owns experiment design, validation, aggregation, and results.
- Collection is permitted only in toolkit-owned instances created for the
  experiment. Existing personal instances are out of scope.

The live development instance is `Voxel Guidance Lab`, in Prism Launcher's
separate `Prism Toolkit` group.

## Initial slices

1. Specify and validate a versioned telemetry/marker envelope.
2. Build the minimal Fabric bridge against that contract.
3. Run a short instrumentation rehearsal with no scientific interpretation.
4. Freeze a balanced task battery and analysis plan.
5. Collect repeated sessions before compiling any candidate fingerprint.

Raw event streams, coordinates, world identifiers, and free text remain
owner-private. Public artifacts contain protocols, code, aggregate vectors,
uncertainty, and documented limitations only.

The [version-1 event contract](docs/event-contract-v1.md) and first
implementation slice live in `src/voxel_guidance`: a strict event validator and
a transparent session-feature compiler. It intentionally emits auditable
measurements rather than a learned tensor or claimed fingerprint.

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

`bridge/` contains the Fabric 1.21.1 rehearsal bridge. Recording is off by
default and controlled in-game with `/vg start <task> <protocol>`, `/vg marker
<name>`, `/vg status`, and `/vg stop`. The bridge independently verifies the
toolkit registry, instance marker, and `Prism Toolkit` group before creating a
private session stream.

The frozen pilot schedule, world setup, modpack manifest, and aggregate-only
compiler are under `experiments/labnote_001/`. The pilot is 12 eight-minute
sessions; do not reuse the five rehearsal streams as evidence.

Labnote 004 applies the shared `apparatus/state-encoding` serializers to the
frozen 120-second feature windows. It establishes lossless JSON and compact
typed-token transport plus UTF-8 size baselines. Its exploratory `qwen3:8b`
probe found compact 5/12 versus prose 3/12 and JSON 2/12, explicitly too small
and post hoc to establish a reasoning advantage.

Labnote 005 tests whether a semantic namespace can replace the full field
dictionary. It cannot in this zero-shot probe: namespace-only matched the opaque
control exactly, while the full dictionary retained the strongest score.

## Local live-guidance prototype

Bridge 0.3.0 can display a session-bound hint written by the local shadow
sidecar. The sidecar remains silent until 120 seconds, emits at most one hint
for a neutral `live-guidance` session, and never controls Minecraft. Train its
local four-task prototype with `compile_guidance_model.py`, then run
`run_shadow_guidance.py` against the owned instance's private session folder
and guidance mailbox. The model is protocol-bound and cannot infer arbitrary
intent.
