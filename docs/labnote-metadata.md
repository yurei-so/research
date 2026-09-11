# Labnote metadata

Labnotes remain ordinary, pleasant Markdown. A small YAML front matter block
provides the stable index data needed by the future GitHub Pages projection,
hover previews, tag pages, timelines, lineage, and backlinks.

```yaml
---
schema_version: 1
id: prosody-011
title: Reproducible synthetic conversational-audio rerun
date: 2026-08-23
status: complete
outcome: inconclusive
question: Does Labnote 003 persist with locally generated, fidelity-gated audio?
tags:
  - conversational-prosody
  - synthetic-audio
  - provenance-repair
  - negative-result
lineage:
  - prosody-003
relations: [{"target":"prosody-003","type":"replicates","rationale":"Repeats the original test with locally generated, fidelity-gated audio."}]
publish: true
---
```

## Fields

- `schema_version` — metadata contract version; currently `1`.
- `id` — globally stable lowercase ID. Use `<family>-NNN`; never reuse it.
- `title` — human-readable title without the ID prefix.
- `date` — protocol publication or authoritative run date as `YYYY-MM-DD`.
- `status` — workflow state: `planned`, `running`, `awaiting-review`,
  `complete`, or `aborted`.
- `outcome` — epistemic result: `positive`, `negative`, `mixed`,
  `inconclusive`, `pending`, or `not-applicable`.
- `question` — one-sentence research question used in indexes and previews.
- `tags` — controlled discovery terms, not prose or authorization labels.
- `lineage` — zero or more stable labnote IDs that this note follows.
- `relations` — optional explicit, typed links to other labnotes. Each relation
  has a `target`, `type`, and short factual `rationale`. Supported types are
  `motivated-by`, `reuses-data`, `reuses-apparatus`, `extends`, `ablates`,
  `replicates`, `supports`, `challenges`, and `supersedes`. These authored
  relationships—not inferred similarity—drive project graphs.
- `publish` — whether the note belongs in the public Pages projection.

`status` and `outcome` stay separate. A completed experiment may have a
negative or inconclusive outcome; those are valid research records, not failed
repository workflows.

## Tag families

Prefer a small composable vocabulary:

- Domain: `conversational-prosody`, `composition`, `turn-taking`,
  `speculative-execution`.
- Method: `synthetic-audio`, `real-audio`, `constrained-decoding`,
  `blinded-review`, `counterfactual`, `deduplication`.
- Concern: `latency`, `safety`, `provenance`, `naturalness`, `human-review`.
- Finding: `positive-result`, `negative-result`, `mixed-result`,
  `inconclusive-result`.

Do not encode privacy, credentials, actor authority, or unpublished private
artifact locations in tags. Publication remains an explicit projection choice.

Internal note links should remain ordinary relative Markdown links. The Pages
renderer may enrich them with hover previews, but the source must stay useful
without JavaScript or the site build.
