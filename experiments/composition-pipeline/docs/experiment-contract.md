# Runtime Roost experiment contract

Composition Pipeline experiments run through an approval-gated one-shot experiment
manager. They are not roost members, handoffs, agents, or independent accelerator
clients.

The ownership boundary is:

1. An operator registers a fixed definition in the scheduler using an absolute
   repository root and the absolute `scripts/run-experiment` path.
2. The scheduler owns request persistence, revision-bound approval, the complete
   non-preemptive accelerator lease, timeout enforcement, output limits,
   private logs, audit, and restart recovery.
3. The repository runner validates a fixed experiment identifier and executes
   only `experiments/<identifier>/run.py` from this repository.
4. The experiment writes bounded machine-readable results to standard output and
   diagnostics to standard error. The scheduler captures both privately.

The runner deliberately provides no shell mode, arbitrary executable option,
network setup, scheduler integration, or accelerator ownership. Definitions
must keep arguments and environment fixed and reviewable.

Copy `config/experiment-definitions.example.json`, replace `USER` with the
deployment account, and merge its definition into the scheduler's managed
experiment definition file. The checked-in `contract_smoke` entry is CPU-only
and exists solely to verify admission and execution wiring; real composition
experiments may use the accelerator only while the scheduler holds their lease.

## Repository-local campaigns

`composition_pipeline.campaign` expands a committed JSON matrix into stable,
content-addressed trials and executes them sequentially inside one approved
experiment process. A campaign manifest fixes its axes, repetitions, retry
limit, total trial ceiling, and early-stop rules before intake. It cannot add
commands or extend its budget while running.

The caller must provide a fixed private state directory in the scheduler
definition. Checkpoints are owner-only, written atomically after each terminal
trial, and bound to the complete manifest digest. Restarting the same frozen
campaign skips completed trial identities; changing the manifest requires a new
state directory and approval revision.

Only flat scalar metrics and opaque trial identities appear in the public
campaign summary. Parameters and trial results remain in the private checkpoint
for later repository-owned aggregation or blinded review. Trial execution is
strictly sequential. The campaign engine does not acquire leases, start worker
processes, or provide an arbitrary driver interface.

First-class campaign scheduling in the compute broker is intentionally deferred.
Until then, the broker and scheduler see one bounded, non-preemptive experiment lease.
