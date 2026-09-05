# Labnote 001: Prompted and constrained editing baseline

Date: 2026-08-22

## Hypothesis

An existing instruct model can produce deterministically applicable
virtual-buffer operations reliably enough that fine-tuning is not yet
justified.

## Frozen protocol

- Experiment: `labnote_001`
- Agent Runtime run: `475d0615-ba0f-4b12-aa31-24a9dd3bcba1`
- Model: `qwen3:8b`
- Seed: `20260822`
- Temperature: `0`
- Corpus: six frozen, non-sensitive writing cases
- Arms: append-only, unconstrained JSON editing, and schema-constrained JSON
  editing
- Accelerator ownership: one non-preemptive roostd experiment lease

The committed protocol and corpus are the authoritative inputs. Generated text
remains in Agent Runtime's private artifact store and is not reproduced here.

## Runtime result

The run completed successfully with exit code 0 in approximately 24 seconds.
It released its accelerator lease normally, left the queue empty, produced an
empty stderr log, and retained its stdout artifact with owner-only permissions.

| Editing arm | Parse success | Semantic application success | Finalize success |
| --- | ---: | ---: | ---: |
| Unconstrained JSON | 6/6 (100%) | 5/6 (83.3%) | 5/6 (83.3%) |
| Schema-constrained JSON | 6/6 (100%) | 6/6 (100%) | 6/6 (100%) |

The unconstrained arm failed the `friendly-technical` case because it did not
finalize the document. The schema-constrained arm completed all six cases.

## Interpretation

The schema-constrained arm cleared the frozen protocol's 95% mechanical
reliability gate. On this evidence, fine-tuning is not justified. Constrained
decoding is sufficient to continue testing the interface with the existing
model.

This is not evidence that iterative editing improves writing. Both editing arms
reported zero edit operations: successful cases primarily supplied a final
buffer rather than exercising append, replace, or delete transitions. The
experiment therefore established protocol reliability, not composition quality
or the value of revision.

The six-case corpus is intentionally small. A single deterministic run cannot
establish general reliability, compare semantic quality, or support a model
training decision.

## Disposition

- Do not fine-tune.
- Preserve this run as the mechanical baseline.
- Keep generated texts private until they receive a blinded quality review.
- In the next experiment, begin from a seeded draft and require at least one
  valid revision operation before finalization.
- Compare constrained revision against direct generation using blinded human
  judgments for instruction adherence, correctness, concision, and voice.
- Revisit training only after repeated constrained-protocol failures that
  cannot be resolved through the interface, schema, or prompt design.
