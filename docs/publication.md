# Public research projection

The GitHub Pages site is a generated, allowlisted projection of canonical
labnotes. It is not a mirror of the repository.

## Publication boundary

A labnote is eligible only when its versioned front matter contains
`publish: true`. The catalog compiler emits a fixed set of metadata fields and
the rendered Markdown body for eligible notes. It never copies experiment
directories, artifacts, raw recordings, private review state, machine-local
inputs, or arbitrary repository files into the Pages artifact.

Setting `publish: false` keeps the canonical labnote in the research record but
omits its metadata and body from every generated public view. A published note
may not name an unpublished note as a lineage target because that would leak
the private note's stable identity.

## Local verification

```sh
npm test
npm run catalog:check
npm run build
```

The generated site is written to ignored `dist/`. The build uses the current
Git revision and its commit time, making repeated builds from the same revision
stable. Serve `dist/` with any local static-file server to inspect the exact
Pages artifact.

## Continuous deployment

The Pages workflow runs only for `main` and manual dispatch. It checks the
metadata contract and tests before building. GitHub receives only `dist/` as
the deployment artifact. The workflow has read-only repository access plus the
minimal Pages and identity-token permissions required for deployment.

The public manifest drives the research-area index, labnote list, filters,
outcome counts, labnote routes, and future feeds. Those views must not grow
independent hand-maintained indexes.
