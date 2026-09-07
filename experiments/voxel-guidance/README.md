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

