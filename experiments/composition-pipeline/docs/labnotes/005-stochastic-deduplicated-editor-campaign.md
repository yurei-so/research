# Labnote 005: Stochastic deduplicated optional editor campaign

Date: 2026-08-23

## Hypothesis

A modest nonzero sampling temperature can produce enough distinct optional
editor outcomes to support a useful conditional blind review, provided exact
duplicate answer pairs are removed before operator intake and remain visible as
multiplicity telemetry rather than independent samples.

## Frozen protocol

- Experiment: `labnote_005`
- Agent Runtime run: `c7537f90-1641-45fc-b198-fae9d87132e0`
- Campaign digest: `0927d8781e5e5bc262a72bf52e8d4840c5196f02389f50969608b9269825f002`
- Repository revision: `73c9f2e`
- Model: `qwen3:8b`
- Temperature: 0.35
- Base seed: 20260825, varied by repetition
- Matched assignments: 120
- Execution trials: 240
- Protocol revision: `stochastic-deduplicated-review-v1`
- Accelerator ownership: one non-preemptive roostd experiment lease

Each optional result is self-matched against its exact pre-editor candidate.
Normalized-identical outputs become automatic ties. Normalized unordered
changed pairs are content-hashed globally, and exactly one representative from
each unique group enters blinded review. Duplicate multiplicity is retained as
aggregate telemetry but cannot inflate the manual sample.

Raw prompts, drafts, generated text, edit operations, pair hashes, mappings,
and review artifacts remain in owner-only private state.

## Runtime and uniqueness result

The campaign completed 240/240 execution trials with no campaign failures,
empty stderr, and a normal accelerator-lease release.

| Measurement | Count |
| --- | ---: |
| Matched assignments | 120 |
| Automatic ties | 92 |
| Changed trials | 28 |
| Unique changed answer pairs | 21 |
| Duplicate changed trials removed from review | 7 |
| Optional editor protocol success | 73/120 |
| Valid unchanged decisions | 44 |
| Voluntary edit decisions | 29 |
| Transactional fallbacks | 47 |

The changed-pair multiplicities were sixteen singleton groups, three groups of
two, and two groups of three. One voluntary edit normalized to no textual
change, leaving 28 changed trials. The 21 unique pairs span seven task/style
cells. The private operation aggregate contains one append, two deletes, and 61
replacements.

The public blinded bundle digest is
`3628dae66aeb0ed93fe4e7f575f1f6f6b4f3e42a3178534c6d00c6fe75057929`.

## Blinded human review result

The owner completed all 21 unique locked judgments on 2026-08-23. The reveal
gate opened only after the final judgment was durably committed against the
original bundle digest.

| Preferred arm | Unique pairs | Share |
| --- | ---: | ---: |
| Direct rewrite | 11 | 52.4% |
| Optional editor access | 10 | 47.6% |
| Tie | 0 | 0% |

An exact two-sided binomial test gives `p = 1.0`. The deduplicated conditional
review therefore provides no evidence of a preference advantage for either
arm.

Restoring each unique changed pair's observed generation multiplicity gives a
descriptive changed-trial frequency of 12 direct preferences and 16 optional
preferences. Restoring the 92 automatic ties produces an all-assignment
frequency of 12 direct, 16 optional, and 92 ties. These weighted counts describe
the generated campaign; duplicate occurrences were not independently judged
and must not be treated as independent preference evidence.

## Cost

| Arm | Mean generated tokens | Mean prompt tokens | Mean latency | Generations |
| --- | ---: | ---: | ---: | ---: |
| Direct rewrite | 33.72 | 91.00 | 0.614 s | 1 |
| Optional editor access | 98.08 | 319.55 | 1.570 s | 2 |

Optional access used about 2.9 times the generated tokens, 3.5 times the prompt
tokens, and 2.6 times the latency. It also had a 39.2% protocol-failure rate.

## Disposition

- Do not promote or fine-tune optional editor access from this campaign.
- Temperature 0.35 plus content-hash deduplication successfully improved review
  diversity from 2 unique pairs in Labnote 004 to 21 in Labnote 005.
- Among genuinely changed unique outputs, human preference was effectively
  even; the extra editor pass did not justify its compute cost.
- Preserve self-matching, automatic ties, pre-intake deduplication, and separate
  unique versus multiplicity-weighted reporting as infrastructure.
- A future campaign should expand genuinely distinct tasks and target known
  residual defects after direct rewrite rather than repeat this same corpus.
- Candidate text, pair-level judgments, hashes, and treatment mappings remain
  in owner-only private state and are not reproduced here.
