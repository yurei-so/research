# Yurei Research

This repository is the canonical lab bench for Yurei's legitimate AI research.
It keeps experimental implementations, frozen protocols, evaluation fixtures,
human-review apparatus, results, and the provenance needed to reproduce or
interpret them in one place.

## Repository shape

- `experiments/` — bounded research projects and their labnotes.
- `apparatus/` — reusable evaluation, annotation, and review tools.
- `demos/` — research-derived demonstrations that preserve an experimental
  connection but have their own runnable surface.
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

## Licensing

This is a mixed-license repository. Research-library and research-instrument
software is AGPL-3.0-only so network-deployed modifications preserve a source,
self-hosting, and forking path. General apparatus and reusable infrastructure
use the permissive MIT License. Research writing, datasets, and artifacts are
separate licensing questions and are not automatically covered by either
software license. See [the path-specific licensing policy](LICENSE.md).

## Public research library

The research library site is a generated public projection, not a repository
mirror. Labnotes opt in with `publish: true`; the build validates their
metadata and emits only the allowlisted catalog and rendered eligible notes.
See the [publication boundary and local build](docs/publication.md).
