# Yurei Research

This repository is the canonical lab bench for Yurei's legitimate AI research.
It keeps experimental implementations, frozen protocols, evaluation fixtures,
human-review apparatus, results, and the provenance needed to reproduce or
interpret them in one place.

## Repository shape

- `experiments/` — bounded research projects and their labnotes.
- `apparatus/` — reusable evaluation, annotation, and review tools.
- `docs/` — repository-wide governance, migration records, and decisions.
- `references/` — pointers to projects that graduated into standalone repos.

An experiment may graduate when it becomes a substantial reusable library,
service, or tool. Graduation moves product ownership, not the research record:
this repository retains protocols, results, provenance, and a durable reference
to the standalone project.

See [research governance](docs/governance.md), the
[experiment inventory](docs/experiment-inventory.md), the
[labnote metadata contract](docs/labnote-metadata.md), and the
[migration ledger](docs/migration-ledger.md).
