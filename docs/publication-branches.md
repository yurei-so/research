# Publication branches

Yurei Research separates authored source from generated publication output.

- `main` is the stable authored source.
- `beta` is the non-canonical preview source.
- `gh-pages` is generated output only and must never be edited by hand or
  merged back into an authored branch.

The beta workflow builds and validates `main` and `beta` independently. It then
assembles only their allowlisted `dist/` trees, placing stable output at `/` and
beta output at `/beta/`. The assembler rejects symlinks and unexpected file
types. Beta HTML is marked `noindex,nofollow`, beta robots disallow crawling,
and `deployment-manifest.json` records both source revisions.

Beta is a human-facing presentation preview only. It may change layout,
navigation, or visual interpretation aids, but it does not create a second
version of any labnote or research tool. Dedicated research JSON, corpus,
agent-overview, graph-data, sitemap, and agent-discovery files are omitted from
`/beta/`; those machine-readable contracts remain available only on stable.
Visual pages carry the minimum embedded data needed for their human-facing
interactions. The stable source owns the assembler and its list of approved beta family IDs.
A switch appears only on a listed family with both builds present and identical embedded published evidence and authored relations. Stable is
the default. The homepage, labnotes, dispatches and other pages have no beta
switch. Ineligible legacy preview URLs forward to stable. The deployment
manifest records the pinned source revisions.

GitHub Pages publishes from the generated `gh-pages` branch. A source change on
either `main` or `beta` rebuilds both pinned channels before atomically updating
that branch; authored branches are never served directly.

Every generated-branch commit must be produced by the workflow after both
source builds, their tests, catalog validation, and privacy checks pass. A
failure leaves the previous generated commit intact.
