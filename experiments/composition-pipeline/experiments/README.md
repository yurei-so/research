# Experiments

Keep hypothesis-specific implementations in numbered experiment directories.

`campaign_smoke` is a CPU-only contract fixture for the reusable sequential,
resumable campaign engine. Real campaigns remain numbered experiments with
committed manifests and fixed Agent Runtime definitions.

`labnote_002` is the first model-backed campaign. It compares direct rewriting
with mandatory schema-constrained revision and produces a private blinded A/B
review bundle.
