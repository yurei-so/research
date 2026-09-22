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

The build also emits `research-corpus-v1.json`, the provider-neutral interchange
consumed by `research-tools`. It includes only the public family and labnote
fields needed for reusable provenance and attention instruments. No tool is
granted access to canonical private working state; publication/export is the
only bridge between the two security domains.

Agent discovery begins at `llms.txt` and `agent-overview-v1.json`. Each family
also exposes a token-bounded `projects/<family>/index.json` orientation document
through an HTML `rel="alternate"` link. These overviews select at most three
evidence-routing entry points: the latest work, latest negative result, and
earliest published record. They explicitly distinguish published evidence,
human-authored provenance, lossy similarity geometry, and generated summaries.
The compact family view is limited to 4096 bytes; complete records and heavy
geometry remain opt-in links rather than default payloads.

The build renders the complete public catalog into static HTML before the
optional filtering script runs. It also emits canonical URLs, descriptive
per-note metadata, valid `TechArticle` microdata, `robots.txt`, and a generated
`sitemap.xml`. Each public note links to its canonical source record. Search
discovery does not weaken the publication boundary: only eligible labnotes are
included in any of these surfaces.

Because this is a GitHub Pages project site under `/research/`, only a site at
the `yurei-so.github.io` origin root can publish the origin-authoritative
`/robots.txt`. The project-local file documents the intended allow policy and
advertises the sitemap when fetched directly; Search Console should also be
given `https://yurei-so.github.io/research/sitemap.xml` explicitly.

The compiler also derives publication-safe reverse lineage. A note's `lineage`
field supplies its direct predecessors; the public manifest adds `relations`
with `follows` and `continued_by` IDs. Individual note pages render that local
timeline directly into static HTML. Unpublished notes cannot appear as either
side of a public relationship.
