# Labnote 006

This campaign tests diagnosis-guided repair of residual defects in direct
rewrites. Each trial generates a baseline, asks for one primary defect from a
frozen taxonomy, permits one narrowly scoped exact-buffer repair only when a
defect is found, applies the returned complete buffer as one exact replacement,
and independently verifies that the named defect was fixed
without a material regression.

Unchanged, unverified, and duplicate answer pairs never enter human review.
The review gate requires at least 12 unique verified repairs spanning at least
six cases. Candidate text, diagnostic evidence, mappings, and pair-level
telemetry remain in owner-only state.
