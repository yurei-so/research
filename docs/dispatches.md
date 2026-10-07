# Dispatches

Dispatches are human-readable, story-shaped accounts of engineering work. They
sit beside labnotes, not above them: a Dispatch can explain why a result matters
and how the work felt, while the labnote remains the canonical experimental
record. A Dispatch is not evidence by itself and must not make a stronger claim
than its cited or described observations support.

## Voice and evidence

The voice may be lively, irreverent, and theatrical—even mock-military in an
after-action-report way. Keep the observation ledger precise. Each Dispatch
should make it easy to tell apart:

- what was directly observed or measured;
- what the author thinks that observation means; and
- what remains untested.

Humor belongs in the narration, not in altered measurements. Don't turn a
successful control/baseline into a claim that the system under study succeeded.
Link formal research records where they exist; never invent a labnote citation
just to make the page look official.

## Metadata contract

Dispatches are ordinary Markdown under `dispatches/`. Front matter is a small,
strictly allowlisted public schema:

```yaml
---
schema_version: 1
id: dispatch-001
title: After-action report
date: 2026-10-05
status: draft
lede: One short human-facing orientation.
tags: [engineering, field-test]
related_labnotes: []
publish: false
---
```

- `id` is globally stable within Dispatches and uses `dispatch-NNN`.
- `status` is `draft`, `review`, or `published`.
- `publish: true` is required for any Pages output and also requires
  `status: published`.
- `related_labnotes` contains only stable labnote IDs; this type does not alter
  labnote lineage or the machine-readable experimental corpus.
- Unknown metadata is rejected so private bookkeeping cannot accidentally be
  projected into public metadata.

`publish: false` excludes a Dispatch from generated Pages files and the sitemap.
It does **not** make the Markdown private if the repository change is committed
to the public source repository. Keep an unpublished draft local until its
content and publication are separately reviewed.

Dispatches receive a separate human-readable route and index. They are not
included in `research-corpus-v1.json`, family evidence summaries, labnote
counts, outcome rates, or agent evidence overviews.

## Media embeds

Raw HTML is not enabled in dispatch Markdown. A narrowly validated block
directive can embed a YouTube video by its 11-character ID:

```text
:::youtube tR0AT65-AZs "Descriptive video title"
```

The page generator builds the iframe using YouTube's privacy-enhanced
`youtube-nocookie.com` host, lazy-loads it, sends only the site origin as its
cross-origin referrer, and keeps a direct Watch on YouTube link beneath it.
The origin-only referrer is required for YouTube's embedded player identity;
suppressing it produces player Error 153. The dispatch-page Content Security
Policy permits frames only from that exact host. Loading the player still
contacts YouTube; use an ordinary link instead when a dispatch should not make
that third-party request.
