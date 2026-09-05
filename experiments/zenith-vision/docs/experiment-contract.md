# Runtime Roost experiment contract

Zenith Vision uses Agent Runtime's fixed one-shot experiment manager. The
repository does not acquire an accelerator, start a runtime, or call roostd.

Agent Runtime owns approval, persistence, the complete non-preemptive roostd
lease, timeout and output limits, private logs, audit, and recovery. This repo's
runner accepts only committed experiment identifiers and executes their fixed
entrypoints. Results on standard output are bounded JSON; diagnostics go to
standard error.

The runner executes through the repository-owned `.venv` when installed. This
keeps dependencies explicit under Agent Runtime's intentionally minimal process
environment.

`contract_smoke` is CPU-only and verifies wiring plus the authority invariant.
Future GPU experiments must be registered as distinct, revision-bound
definitions with fixed arguments and environment. A queued experiment may be
overtaken by higher-priority work, but once its lease begins it is never
preempted.
