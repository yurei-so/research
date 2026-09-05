# Zenith Vision

Experiment-first perception and context fusion for Guild Wars 2.

Zenith Vision tests a strict observation boundary before any model or UI is
promoted into Zenith:

- MumbleLink is authoritative for live game state such as map, position,
  heading, character, combat state, and camera orientation.
- Vision contributes only observations that telemetry cannot provide.
- Conflicting visual guesses never overwrite authoritative telemetry.
- Stale or disconnected telemetry becomes unavailable rather than being
  guessed from pixels.
- Every fused field carries provenance suitable for evaluation and audit.

The first checked-in experiment is CPU-only. It validates the contract and the
fail-closed fusion policy without downloading a model or reading a screen.

Current research is now focused on semantic UI recognition. The first bounded
task distinguishes whether an approved objectives, skill-bar, or minimap crop is
present, absent, or uncertain. It is an abstaining evaluation baseline, not a
production detector. Zenith App remains the owner of all live application and
telemetry behavior.

The latest one-shot experiment combines current MumbleLink state, allowlisted
panel recognition, and map metadata served by Zenith App into deterministic
situational guidance. It has no model prompt, polling loop, or second API client.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
python3 -m unittest discover -s tests -v
./scripts/run-experiment contract_smoke
```

With Guild Wars 2 and Zenith App's loopback relay already running, execute one
ephemeral interpreted scene with:

```bash
./scripts/run-interpreted-scene-once
```

The fixed runner prefers `.venv/bin/python` when present so Agent Runtime uses
the repository's declared dependencies rather than ambient system packages.

See [docs/architecture.md](docs/architecture.md),
[docs/data-policy.md](docs/data-policy.md), and
[docs/experiment-contract.md](docs/experiment-contract.md).

The first real semantic result is recorded in
[Labnote 007](docs/labnotes/007-small-ui-panel-recognition.md).
