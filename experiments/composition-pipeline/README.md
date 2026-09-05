# Composition Pipeline

Experimental middleware for model-directed composition, revision, and finalization.

The repository contains bounded composition experiments and reusable campaign
infrastructure. Campaigns expand committed matrices into sequential trials with
manifest-bound private checkpoints; they do not schedule accelerator work.

## Repository shape

```text
docs/          Architecture, policy, roadmap, and experiment labnotes
examples/      Small runnable examples
experiments/   Isolated experiment implementations
import/        Untracked local experiment inputs
scripts/       Development workflow helpers
src/           Installable Python package
tests/         Automated tests
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for the local workflow.
See [docs/experiment-contract.md](docs/experiment-contract.md) for registration
with Agent Runtime's approval-gated roostd experiment path.
