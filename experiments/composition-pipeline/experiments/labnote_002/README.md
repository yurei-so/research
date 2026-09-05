# Labnote 002: Seeded mandatory-revision campaign

## Question

Does schema-constrained revision of a seeded draft produce mechanically reliable
and qualitatively preferable results compared with a direct rewrite?

## Design

Six frozen drafts with known defects cross two arms, two prompt styles, and two
repetitions for 48 sequential trials. The revision arm begins with the draft in
its virtual buffer and must apply at least one mutation before finalization.

Raw prompts, drafts, generated texts, checkpoints, and the arm-reveal key remain
private. The runner creates deterministic randomized A/B pairs for later blinded
operator scoring. Standard output contains only campaign totals, per-arm
mechanical success rates, and an opaque review-bundle digest.

## Interpretation boundary

Protocol success advances outputs to blinded review; it does not establish
writing quality. No model training is performed or justified by this campaign.
