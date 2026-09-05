# Labnote 004: Changed-output optional editor campaign

Date: 2026-08-23

## Hypothesis

Optional editor access may be useful specifically when it chooses to change a
direct rewrite, even if most assignments appropriately remain unchanged. A
larger campaign can estimate both overall usefulness and preference conditional
on a genuine editor-caused change without requiring the owner to review
identical texts.

## Frozen protocol

- Experiment: `labnote_004`
- Authoritative Agent Runtime run: `022e7150-5919-4b04-b487-3788d147383f`
- Campaign digest: `5830372282046620e565625852690e99d5af0c9495c6a09163cff19fbcf9f9e0`
- Repository revision: `5dd2b97`
- Model: `qwen3:8b`
- Matched assignments: 120
- Execution trials: 240
- Protocol revision: `self-matched-changed-output-review-v2`
- Accelerator ownership: one non-preemptive roostd experiment lease

Each optional-editor trial preserves its own pre-editor candidate as the direct
rewrite baseline. Narrow normalization covers only line endings, trailing
horizontal whitespace, and outer whitespace. A normalized-identical final
output becomes an automatic tie. Every normalized-different final output enters
blinded review regardless of edit size, protocol validity, similarity, or
expected quality.

The all-assignment estimand includes automatic ties. The conditional estimand
uses blinded human preference only among genuinely changed outputs. Neither may
be substituted for the other.

Raw prompts, drafts, generated texts, operations, telemetry, review pairs, and
the reveal key remain in owner-only private state.

## Runtime result

The authoritative campaign completed 240/240 execution trials with no campaign
failures, empty stderr, and a normal accelerator-lease release.

| Measurement | Count |
| --- | ---: |
| Matched assignments | 120 |
| Automatic ties | 100 |
| Blinded human-review pairs | 20 |
| Direct rewrite protocol success | 120/120 |
| Optional editor protocol success | 60/120 |
| Valid unchanged decisions | 40 |
| Voluntary edits | 20 |
| Transactional fallbacks | 60 |

The private operation aggregate contains 30 replacements and 10 deletions. The
public blinded bundle digest is
`92f6f2270407253d3919bda7ce0532477682c63f5c783e5b07abc2caa702d0fe`.

An earlier diagnostic run produced 22 differing final pairs but only 20 actual
editor changes because independently repeated baseline generations diverged in
two cases. It was rejected before human review. The authoritative v2 protocol
self-matches the final output to the exact pre-editor candidate and yields the
expected 20/20 correspondence. The diagnostic run is preserved but must not be
used for inference.

## Blinded review and duplicate audit

The owner completed all 20 locked judgments on 2026-08-23. The raw manual
aggregate was 10 direct-rewrite preferences, 10 optional-editor preferences,
and no selected ties. Restoring the 100 automatic ties gives an all-assignment
aggregate of 10 direct, 10 optional, and 100 ties.

A post-review content-hash audit found that the 20 manual items contained only
two unique unordered answer sets, each repeated ten times. All ten repetitions
in one task/style cell were byte-identical after normalization, as were all ten
in the other cell. Temperature-zero greedy decoding therefore collapsed the
seeded repetition axis and created pseudoreplication.

| Unique task/style cell | Direct preferences | Optional preferences |
| --- | ---: | ---: |
| `checkpoint-clarity` / `concise` | 8 | 2 |
| `status-note` / `preservation_first` | 2 | 8 |

The repeated judgments provide a limited intra-rater consistency signal, not
twenty independent quality comparisons. At the unique-pair level, one case
favored each method. Candidate text and pair-level mappings remain private.

## Disposition

- Do not use the 10/10 raw aggregate as evidence of equal arm quality.
- Treat Labnote 004 as a diagnostic demonstration of automatic-tie filtering,
  self-matching, and deterministic repetition collapse.
- Deduplicate normalized unordered answer pairs before future human intake and
  preserve multiplicity only as telemetry.
- Increase statistical breadth primarily with distinct tasks. If repeated
  stochastic samples are desired, freeze a modest nonzero temperature, unique
  seeds, and a pre-review uniqueness audit.
- Do not promote or fine-tune from this campaign.
