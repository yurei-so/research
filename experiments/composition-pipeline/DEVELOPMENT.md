# Development

Composition Pipeline uses the lightweight Python development layout shared by
the sibling pipeline repositories.

## Requirements

- Python 3.11 or newer
- Bash
- Python `venv` support

## Virtual environment

```bash
scripts/venv create
scripts/venv install
scripts/venv run python -m unittest discover -s tests
scripts/run-experiment contract_smoke
```

Generated environments, package artifacts, local imports, and experiment
outputs are intentionally excluded from version control.

## Project boundaries

Keep reusable protocol and state primitives in `src/`, runnable demonstrations
in `examples/`, and hypothesis-specific work in numbered experiment folders.
Each experiment should receive a corresponding labnote before its results are
treated as architectural evidence.

`scripts/run-experiment` is the stable executable boundary used by Agent
Runtime definitions. It accepts a repository-owned experiment identifier, then
replaces itself with that experiment's `run.py`. It does not acquire accelerator
leases, perform approval, or choose arbitrary commands.
