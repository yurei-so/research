# Localized panel transfer

Extracts frozen MobileNet V3 Small embeddings from a fixed set of Hero
header/icon-rail and Inventory-grid proposals. Independent multiple-instance
classifier heads learn from sample-level labels and score only their matching
region family.

Heads use a deterministic full-batch, class-balanced multiple-instance
objective. This prevents sample order from changing the negative-class balance
when new position batches are added.

The current corpus includes the original four environment batches plus three
new Inventory-only development batches staged at left, right, and center panel
positions, plus a Hero-only snowy Hoelbrak batch. Each batch is independently
held out in its own fold.

The experiment performs leave-one-development-batch-out evaluation. Its
promotion gate is frozen at 80% aggregate exact accuracy, at least 70% exact
accuracy in every fold, and no class with more than 20% aggregate false calls
plus misses. It never reads a spent or future holdout and has no live capture or
input-control capability.

When and only when the frozen gate passes, the run trains final heads on all
approved development batches and writes a content-addressed, owner-only JSON
bundle under `~/.local/state/zenith-vision/models/localized-panel`. The bundle
contains numeric weights and provenance digests only; it contains no pixels,
labels, paths, or executable pickle content.
