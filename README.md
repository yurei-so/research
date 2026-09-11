# Yurei Research

This repository is the public corpus and publication surface for Yurei's
legitimate AI research. It keeps published experimental implementations, frozen
protocols, evaluation fixtures, results, and the provenance needed to reproduce
or interpret them. Private working research state is not canonicalized here;
records cross this boundary only through deliberate publication.

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

Reusable corpus inspection machinery lives in
[`yurei-so/research-tools`](https://github.com/yurei-so/research-tools). The
site exports sanitized records as `research-corpus-v1.json`; the tools consume
that documented interchange and never require private working-storage access.

The Pages build also rejects internal note coordinates, private actor names,
deployed RFC1918 addresses, owner-specific home paths, private workstation
hostnames, and internal Runtime run identifiers before publication.
