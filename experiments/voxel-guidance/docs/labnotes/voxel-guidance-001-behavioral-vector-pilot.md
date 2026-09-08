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

### Second in-world rehearsal

A separate `rehearsal-002` stream also validated successfully:

- duration: 194.992 seconds;
- 197 contiguous events: start, 195 position samples, and a clean `stopped`
  boundary;
- event-file permissions: owner read/write only (`0600`);
- derived spatial summary: 7 coarse cells, 223.37 blocks of path distance, and
  0.005 route directness; and
- a distinct session identity and task identity, with no event mixing between
  the two rehearsals.

The second session intentionally contained no marker. It exposed an ambiguity
in the compiler: missing marker latency had been encoded as `1.0`. The compiler
now emits `null` for an unobserved first marker, and the session-set validator
rejects duplicate session identities.

These are instrumentation results only. Inventory, block-action, damage, and
recovery coordinates remain zero because the rehearsal bridge does not emit
those events yet. Multi-session separation passed here; termination behavior
was tested separately below.

### World-exit rehearsal

In `rehearsal-003`, recording was started and the world was exited without an
explicit `/vg stop`. The bridge received the graceful disconnect event and
produced:

- a 5.969-second owner-private stream;
- one start, five position samples, and exactly one clean session end;
- end reason `stopped`;
- a third distinct session identity with no cross-session events; and
- valid compilation with marker latency left unobserved (`null`).

This validates automatic closure on ordinary world exit. It does not validate
hard-crash behavior: the game remained able to execute its disconnect handler.

### Managed debug-crash rehearsal

A second recording reused the human-facing `rehearsal-003` task ID and was
terminated with Minecraft's F3+C debug crash. It created a new UUID-backed file
rather than overwriting the earlier rehearsal. The 39-event stream retained
owner-only permissions, contiguous sequencing, and exactly one end boundary.

F3+C also performs enough orderly shutdown to deliver Fabric's disconnect
callback. The old bridge therefore labeled the end `stopped`, which could not
distinguish explicit stop, world exit, and managed crash. Future bridge output
uses `explicit_stop` for `/vg stop` and the cause-neutral `disconnected` for the
callback. Historical `stopped` streams remain valid. Hard termination without
a callback was therefore tested separately.

### Hard-termination rehearsal

In `rehearsal-004`, the Minecraft window was terminated with `xkill` while
recording. The owner-private stream contains one start and 15 contiguous
position samples, ending at sequence 15 with no session end. The validator
rejects it specifically because its session boundary is incomplete. No repair,
usable feature vector, or synthetic crash end is produced, and the four earlier
recordings remain unchanged.

Phase 0 is complete. Hard-termination handling is deliberately fail-closed:
"recovery" means retaining an auditable incomplete stream while excluding it
from compilation, not guessing how or when the process died. Feature
compilation is deterministic under the same validated event input.

### Full event-surface rehearsal

`rehearsal-005` exercised the expanded bridge in one 76.046-second session. Its
120 contiguous events included 76 positions, 25 coarse inventory deltas, 11
world-confirmed block actions, three health-loss observations, one death, one
later respawn, one setback marker, and a clean `explicit_stop`. All event
channels validated under the version-1 contract.

The death rehearsal exposed a second analysis confound: inventory removal and
recollection around death initially inflated acquisition denominators. The
compiler now excludes inventory deltas from a death until a controlled
`recovered` marker. Nineteen such events were excluded in this rehearsal and
reported as a quality diagnostic. The corrected construction-allocation value
was 0.138 rather than the confounded 0.037. Because no recovery marker was
issued, no post-death inventory activity entered acquisition metrics.

This rehearsal remains apparatus evidence only. Exact item/block identities,
block coordinates, attackers, and raw routes were never emitted.

## Frozen pilot design

The pre-collection protocol is frozen at digest
`320e6bf8a8e2a3978e6125da3be5c2e0b4db52b1e8bea869b41b17225c65877c`.
The live 22-mod apparatus exactly matched manifest digest
`ebcb2db3723b6398b696d7b117b5a5dcee81242ed677d2a3cb97bb3b284acb59`
at freeze time.

The battery contains 12 eight-minute sessions: exploration, acquisition,
construction, and controlled recovery tasks across three seed blocks. Worlds
within a block share a seed but remain separate saves. Task order is rotated
across blocks to reduce simple order effects. Sessions under seven minutes,
over ten minutes, lacking an explicit stop, or missing required markers are
excluded under predeclared rules.

The compiled fingerprint has seven coordinates: exploration breadth, route
closure, plan revision rate, resource selectivity, construction allocation,
recovery efficiency, and deliberation latency. Each coordinate is aggregated
at the seed-block level, receives a 95% block-bootstrap interval, and reports a
leave-one-block-out range. Missing values remain `null`; there is no learned
embedding, imputation, or single combined score.

The compiler refuses incomplete or duplicate session matrices and emits no
session- or block-level vectors. Public projection is limited to aggregate
coordinates, uncertainty, exclusions, protocol and apparatus digests, and the
claim boundary.

The event sources, task battery, and analysis plan are frozen. Pilot collection
may begin in protocol order. None of the rehearsal streams may enter evidence.
