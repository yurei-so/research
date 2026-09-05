# Composition Review

A small, owner-local blinded A/B review surface for text and audio experiment
bundles.

The app shows one pair at a time with identical candidate presentation. A, B,
or Tie commits immediately and cannot be edited. Progress is stored atomically
and resumes after restart. Treatment identity remains server-side until every
pair has a locked judgment, at which point the app reveals aggregate results.
Candidate positions are deterministically counterbalanced to the closest
possible split before the session begins; the source bundle remains immutable.

## Privacy and authority

- The server binds to `127.0.0.1` by default.
- A browser must enroll with an owner-only token before it can read source
  material.
- Review bundles, reveal keys, enrollment tokens, and judgment state live
  outside the repository with mode `0600`; their parent directory is `0700`.
- Public logs contain readiness metadata only, never requests or review text.
- The API enforces fixed pair order and append-only judgments.
- Bundle/key digests must match before the server starts.
- Audio assets are authenticated, constrained to one explicit asset root,
  rejected if symlinked, and SHA-256 verified before intake.

## Run

Set absolute paths for `COMPOSITION_REVIEW_BUNDLE`,
`COMPOSITION_REVIEW_KEY`, `COMPOSITION_REVIEW_STATE`, and
`COMPOSITION_REVIEW_TOKEN`, then run:

```bash
npm start
```

Audio bundles additionally require `COMPOSITION_REVIEW_ASSET_ROOT`. Version 2
audio bundles declare an allowlisted asset manifest, an optional calibration
clip, and opaque candidate asset IDs. The browser must pass a local
headphone/listening-level gate before the first pair appears. Audio URLs remain
authenticated and reveal no filesystem paths. Version 1 text bundles remain
fully supported.

The default address is `http://127.0.0.1:4193`. Navigate once to the owner-only
`/enroll/<token>` URL to set the seven-day HttpOnly browser cookie.

Run the dependency-free test suite with `npm test`.

The checked-in user-service unit under `deploy/` points to the currently selected
workstation review. It binds only to loopback and grants write access only to
that review's private state directory.

`scripts/open-review` reads the owner-only enrollment token without printing it
and launches the default browser. The matching desktop entry can be installed
from `deploy/composition-review.desktop`.
