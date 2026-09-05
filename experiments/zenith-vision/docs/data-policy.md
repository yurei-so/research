# Data policy

- Default to synthetic and licensed public fixtures.
- User screenshots or frames require an explicit collection session and remain
  private unless separately approved for release.
- Collect only the selected game window, never the full desktop.
- Store derived labels and bounded crops where possible instead of raw frames.
- Strip chat, account names, character names, guild text, and other identifiers
  before a frame may enter an experiment corpus.
- Teacher-generated labels are untrusted until verified by a human or a
  precommitted evaluation rule.
- High-frequency MumbleLink samples are ephemeral. Persist only experiment
  fixtures or meaningful, privacy-reviewed summaries.
- Dataset manifests record source class, consent, redaction status, license,
  split, and content digest. Train and evaluation splits are immutable per run.
- Experiment output must not contain screenshots, character names, absolute
  paths, prompts, or private source material. OCR text is prohibited by default.

An operator-approved review candidate is not a dataset item. It is stored in an
owner-only local state directory with a content digest and a receipt containing
no OCR text. Admission requires a later explicit review decision; merely
creating or viewing the candidate grants no training or transfer permission.

Privacy approval admits the reviewed candidate only as an unlabeled private
holdout. It does not make the image training-ready. The admission is bound to
the candidate digest, original consent receipt, non-release license, structural
mask policy, and an explicit `labels_verified: false` record.

Geometry-seeded labels remain proposals until a human reviews a visual overlay.
Masked chat and party/squad regions are excluded from the current proposal;
privacy approval never implies annotation approval.

An approved proposal becomes a separate digest-bound label file. The dataset
manifest, admission record, and proposal status are updated to preserve the
review chain; training and evaluation code reads labels only through that
manifest reference.

Bounded collection sessions revalidate the exact window on every attempt,
apply structural masks before retention, discard perceptual near-duplicates,
and stop at both a candidate ceiling and a wall-clock deadline. A batch remains
outside every dataset until its private contact sheet is approved.

Approved batches are admitted into a separate private test holdout with one
digest-bound admission record per candidate. Batch approval does not produce
labels, change the test split, or authorize training.

When a stable HUD layout is shared across a reviewed batch, the same
item-specific seed boxes may generate annotation proposals for every item. The
boxed contact sheet must be approved before any proposal becomes a label file.

The current UI-layout corpus intentionally covers the Guild Wars 2 Small,
Normal, and Large UI profiles. The Larger/XL profile is explicitly out of scope
and must not be inferred from adjacent profiles.

The operator permits ordinary game text recognized locally from the
independently validated Normal objectives crop to enter private structured
observations. This narrow exception excludes chat, party/squad, character,
account, guild, minimap, and full-frame text. Observations must carry crop
digest, OCR confidence, backend, capture time, and disclosure-policy provenance;
identifier-like patterns fail without output. Low-confidence tokens may be
omitted only when at least half of all tokens and at least three tokens remain;
the observation must then declare itself incomplete and record omitted count
and retained fraction.

For semantic panel recognition, the operator permits local inspection of the
selected Guild Wars 2 window after complete structural masking of chat and
party/squad zones. The recognizer may emit only predeclared panel kinds and
confidence metadata; all other OCR tokens and panel contents are discarded.
The initial allowlist is `inventory` and `hero`. Full frames remain ephemeral.

Interpreted scenes may retain public map and point-of-interest names returned by
Zenith App, bounded game-coordinate distances, allowlisted panel state, and
deterministic guidance. They must not retain prompts, model completions, raw OCR,
frames, or character identity. Retrieval errors are reduced to an error class;
upstream response bodies are not copied into the interpreted result.
