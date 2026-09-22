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
interactions. Revision menus link matching stable and beta routes and identify
the exact source revisions recorded in the deployment manifest.

Updating `gh-pages` does not itself authorize a live deployment. GitHub Pages
remains configured for the existing Actions deployment until an explicit
publication cutover is reviewed and activated. Until then, `gh-pages` is an
inspectable candidate publication surface.

Every generated-branch commit must be produced by the workflow after both
source builds, their tests, catalog validation, and privacy checks pass. A
failure leaves the previous generated commit intact.
