# Pilot collection runbook

This directory freezes the 12-session `pilot-v2`. Rehearsals, automation
smokes, and the superseded pre-automation collection epoch must not enter pilot
inputs.

`collection-ledger.json` records owner-safe acceptance and exclusion receipts.
It deliberately omits raw session identifiers, file paths, routes, events, and
session-level behavioral vectors.

## Automated world preparation

Prism Toolkit creates one owned ephemeral world for every scheduled session,
using the block's exact seed and an attached `pilot-v2` launch recipe. Minecraft
generates the chunks and seed-specific spawn. Separate saves prevent task
activity from contaminating another condition.

The bridge consumes the recipe once, applies survival/day/clear-weather and the
declared inventory preset, waits for client inventory synchronization, displays
the objective, and starts recording. Empty-inventory tasks use `empty`;
construction uses `construction-kit-v1`; recovery uses `recovery-kit-v1`.

At eight minutes the bridge writes and closes `explicit_stop` before quitting
Minecraft. Do not manually stop or exit unless the run must be marked
as interrupted.

Subjective markers remain manual. For explore, acquire, and construct, emit
`plan_started` after deciding the initial plan and `task_complete` when the
objective is personally complete.

For recovery, emit `plan_started` manually. The bridge automatically emits
`setback` and kills the player at two minutes. After respawning, emit
`recovered` only when a viable state has actually been restored, then emit
`task_complete` when the objective is complete.

Complete every block in its frozen order. Do not rerun or replace a session
after seeing compiled results; record interruptions and apply exclusions before
analysis.

The post-collection `compile_state_encoding.py` pass reuses exactly the 12
accepted streams to produce only aggregate serialization sizes, round-trip
fidelity, schema metadata, and the reference task score. It never retains
serialized per-session observations.

`run_state_encoding_model.py` performs the optional local Ollama probe and
retains only aggregate confusion matrices, prompt-token counts, timings, and
repeat-stability checks. It does not retain session-level model predictions or
prompts.

`run_namespace_ablation.py` compares full field semantics, a semantic namespace
alone, a namespace plus group grammar, and an opaque-schema control using the
same aggregate-only retention boundary.
