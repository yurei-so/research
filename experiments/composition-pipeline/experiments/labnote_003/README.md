# Labnote 003: Optional editor-access campaign

## Question

Does offering an editor inspection pass improve user-facing text over the same
deterministic direct rewrite when the model may finalize without making edits?

## Design

The six Labnote 002 cases cross two arms, two prompt styles, and two repetitions.
Both arms first generate the same deterministic direct rewrite. The baseline
returns it immediately. The optional-editor arm receives that rewrite in a
bounded virtual buffer and may either finalize unchanged or voluntarily apply
validated editing operations before finalizing. Zero edits are a valid,
first-class treatment outcome.

The editor is transactional. If the inspection response is invalid or cannot be
applied, the treatment returns the unchanged initial candidate, records a
protocol failure, and remains eligible for blinded review. This prevents invalid
tool use from destroying a usable response and prevents survivor bias from
silently dropping treatment failures.

Raw prompts, drafts, generated texts, operations, checkpoints, telemetry, and
the reveal key remain private. Standard output contains only mechanical validity
counts and an opaque review-bundle digest. Treatment telemetry is analyzed only
after blinded human judgments are complete.

## Interpretation boundary

Protocol success does not establish quality. The optional editor earns its
complexity only if blinded preference justifies its extra latency and compute.
No model training is performed or justified by this campaign.
