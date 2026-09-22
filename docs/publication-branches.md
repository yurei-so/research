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

Updating `gh-pages` does not itself authorize a live deployment. GitHub Pages
remains configured for the existing Actions deployment until an explicit
publication cutover is reviewed and activated. Until then, `gh-pages` is an
inspectable candidate publication surface.

Every generated-branch commit must be produced by the workflow after both
source builds, their tests, catalog validation, and privacy checks pass. A
failure leaves the previous generated commit intact.
