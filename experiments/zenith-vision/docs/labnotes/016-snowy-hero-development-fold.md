# Labnote 016: snowy Hero development fold

## Question

Does adding independently collected Hero-only Hoelbrak development data repair
the snowy Hero weakness exposed by Labnote 015 without regressing Inventory?

## Method

- Private input: eight approved, structurally masked development batches.
- New data: eight Hero-only observations collected in snowy Hoelbrak with
  recognition disabled.
- Spent holdouts: excluded and not read.
- Architecture, threshold, deterministic training objective, and development
  gate: unchanged from Labnote 014.
- Evaluation: eight leave-one-development-batch-out folds.
- Accelerator: RTX 4070 through the non-preemptive roostd experiment lease.
- Run: `f064481f-15ec-4fd1-a9e7-54c13c42591d`.

## Result

| Held batch | Exact accuracy | Hero TP/FP/FN | Inventory TP/FP/FN |
| --- | --- | --- | --- |
| 001 | 9/9 (100%) | 7/0/0 | 2/0/0 |
| 002 | 7/9 (77.8%) | 6/0/1 | 2/0/1 |
| 003 | 11/12 (91.7%) | 8/1/0 | 7/0/0 |
| 004 | 12/12 (100%) | 0/0/0 | 8/0/0 |
| 005 left Inventory | 3/4 (75%) | 0/1/0 | 4/0/0 |
| 006 right Inventory | 4/4 (100%) | 0/0/0 | 4/0/0 |
| 007 center Inventory | 4/4 (100%) | 0/0/0 | 4/0/0 |
| 008 snowy Hero | 8/8 (100%) | 8/0/0 | 0/0/0 |

Aggregate exact accuracy was 58/62 (93.5%). Hero's aggregate error rate was
4.8%; Inventory's was 1.6%. The new independently held snowy Hero fold was
perfect, and the Inventory position folds retained complete recall. The frozen
development gate passed.

The gate emitted content-addressed candidate
`3d37e24ca4e8b57038724062fe87a370c98ec208d5bc0f1663aeb907e40b50f8`,
bound to development corpus
`87a54b2d6a2448f76a86056102e113ed070ed9b2695d25f8bd75844cece91afc`.
The run completed on CUDA with exit code 0 and no stderr, and roostd released
the accelerator lease normally.

## Decision

Accept the candidate as eligible for a different fresh holdout. Do not promote
it to live use and do not reuse either spent holdout. Prefer a later session and
a visually distinct environment to reduce temporal and scene correlation with
the new Hoelbrak development batch.
