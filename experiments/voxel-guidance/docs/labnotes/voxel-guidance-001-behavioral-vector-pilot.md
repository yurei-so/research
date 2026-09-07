---
schema_version: 1
id: voxel-guidance-001
title: "Minecraft behavioral-vector pilot"
date: 2026-09-07
status: planned
outcome: pending
question: "Can repeated, task-balanced Minecraft sessions produce an interpretable behavioral vector whose within-condition variation is smaller than its uncertainty?"
tags: ["behavioral-telemetry","human-in-the-loop","minecraft","planned-experiment","provenance","repeated-measures"]
lineage: []
publish: true
---
# Labnote 001: Minecraft behavioral-vector pilot

## Question

Can repeated, task-balanced Minecraft sessions produce an interpretable
behavioral vector whose within-condition variation is smaller than its
uncertainty?

## Motivation

Open-ended play exposes choices that short text prompts often compress away:
exploration versus exploitation, planning before action, persistence after a
setback, resource allocation, and the tendency to revise or abandon a plan.
Minecraft offers a controllable environment for measuring those choices across
repeated tasks.

The resulting vector is a description of behavior observed under this protocol.
It is not a biometric, an identity claim, a personality test, or evidence about
behavior outside the measured sessions.

## Candidate coordinates

The pilot may evaluate these operational coordinates after the event contract
and task battery are frozen:

- exploration breadth;
- plan depth and revision rate;
- resource selectivity;
- persistence and recovery after setbacks;
- construction versus acquisition allocation;
- route efficiency relative to task completion; and
- voluntary marker timing and confidence.

Coordinates that cannot be defined from observable events before collection
will be removed rather than inferred afterward.

## Collection boundary

- Only the toolkit-owned `Voxel Guidance Lab` instance may emit study data.
- Recording is explicit per session and visibly indicates its current state.
- The bridge must not collect chat, screenshots, microphone input, keystrokes,
  account identifiers, server addresses, or activity outside the game world.
- World and session identifiers are random experiment-local values.
- Raw positions and event streams remain private and are excluded from public
  artifacts.
- Human markers are structured experiment events, not unrestricted journal
  text.

## Staged protocol

### Phase 0: contract rehearsal

Validate start/stop behavior, event ordering, timestamps, session separation,
marker delivery, crash recovery, and deterministic export. This phase makes no
scientific claim and its data cannot enter the pilot analysis.

### Phase 1: task battery freeze

Define a small set of matched tasks spanning exploration, acquisition,
construction, interruption, and recovery. Freeze task seeds or world fixtures,
time limits, allowed assistance, marker prompts, exclusions, and the analysis
code before measured play begins.

### Phase 2: repeated collection

Collect multiple sessions per task condition. Session order should be rotated
when practical. Practice and interrupted sessions remain visible in the ledger
but are excluded under predeclared rules.

### Phase 3: compilation

Aggregate events into task-normalized coordinates. Report per-session values,
within-condition variation, bootstrap intervals over sessions, and leave-one-
task-out sensitivity. Do not collapse the vector to a single score.

## Advancement gate

The pilot earns interpretation only if:

1. the contract rehearsal has no unexplained event loss or cross-session data;
2. every retained coordinate has a frozen operational definition;
3. at least eight usable measured sessions exist across the task battery;
4. uncertainty and leave-one-task-out sensitivity are reported; and
5. conclusions remain explicitly protocol-bound.

Otherwise the outcome is negative or inconclusive and preserved as such.

## Current decision

The version-1 event contract and transparent feature compiler pass their
contract tests. The Fabric bridge built and initialized in an isolated live
launcher rehearsal on 2026-09-07; recording remained off and no world was
opened. A subsequent Accessories/Trinkets compatibility problem in the restored
convenience-mod set was corrected before the in-world rehearsal.

### First in-world rehearsal

After the mod compatibility issue was corrected, a private in-world rehearsal
completed successfully:

- duration: 382.572 seconds;
- 385 contiguous events: start, 382 position samples, one controlled marker,
  and a clean `stopped` boundary;
- event-file permissions: owner read/write only (`0600`);
- sampling cadence: approximately one position sample per second;
- derived spatial summary: 50 coarse 16-block cells, 808.50 blocks of path
  distance, and 0.513 route directness; and
- no raw coordinates or route map were promoted into the research record.

This is instrumentation evidence only. Inventory, block-action, damage, and
recovery coordinates remain zero because the rehearsal bridge does not emit
those events yet. Crash recovery and multi-session separation remain untested,
so Phase 0 is not complete.

Proceed only with the remaining Phase 0 instrumentation checks. Do not collect
pilot evidence until the task battery and analysis plan are frozen.
