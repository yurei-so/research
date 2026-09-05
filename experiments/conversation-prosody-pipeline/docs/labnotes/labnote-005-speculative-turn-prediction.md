# Lab note: Speculative semantic branch and turn-state prediction

**Run date:** 2026-08-13 through 2026-08-14

**Status:** Complete; plan speculation did not earn draft or real-audio escalation

**Execution host:** `mpaiServer-8kl`

## Question

Can semantic branch prediction during an unfinished human turn safely hide language
model latency, while a turn-state estimator reduces premature interruption and
supports optional collaborative completion?

## Scope

Labnote 005a is an offline synthetic timed-replay experiment. It contains 200 authored
turns with incremental transcript snapshots and authored turn-state proxies. It does
not contain recorded audio, measured prosody, or a live assistant. Its purpose is to
validate branch lifecycle, commit policy, late-reversal handling, and experimental
instrumentation before testing real streaming speech.

The corpus is balanced across direct requests, late semantic reversals, hesitation,
longer explanations, and collaborative-completion opportunities. Each turn has four
snapshots, a true endpoint, an earliest safe semantic-commit annotation, and a final
semantic endpoint contract.

## Conditions

| ID | Turn detector | Branch input | Speculative work |
|---|---|---|---|
| A | Fixed 700 ms silence | None | None |
| B | Turn-state model | None | None |
| C | Turn-state model | Transcript | Response plan |
| D | Turn-state model | Transcript plus authored state proxies | Response plan |
| E | Turn-state model | Transcript plus authored state proxies | Plan plus draft |

Conditions C through E are evaluated only as private computation. Nothing is spoken.
Thresholds from 0.50 through 0.90 are swept after inference; no single threshold is
chosen from test outcomes and then presented as preregistered.

## Prediction matrix

- 200 turns;
- four snapshots per turn;
- transcript-only and transcript-plus-state inputs;
- `gemma3:4b` and `qwen3:8b`; and
- three seeds.

The matrix contains 9,600 checkpointed predictions. Primary diagnostics are premature
commit rate, final endpoint accuracy, usable speculative branch rate, late-reversal
invalidation, and milliseconds of correct work available before true turn end.

## 005a results: prediction and turn policy

All 9,600 prediction tasks completed with zero failures and zero service restarts.
The initial analysis incorrectly shared one threshold between private branch creation
and public turn commit. The corrected analysis independently swept those decisions.
The strongest operating points used a permissive 0.50 private branch threshold and
a conservative 0.90 public commit threshold.

| Condition | Best configuration | Premature commit | Early reusable branch | Median head start | Final endpoint accuracy |
|---|---|---:|---:|---:|---:|
| A | Fixed 700 ms silence | 40.00% | n/a | n/a | n/a |
| B | `qwen3:8b`, authored state proxies, commit 0.80 | 0.00% | n/a | n/a | 59.83% |
| C | `gemma3:4b`, transcript, branch 0.50 / commit 0.90 | 0.00% | 37.00% | 1,200 ms | 61.00% |
| D/E | `gemma3:4b`, authored state proxies, branch 0.50 / commit 0.90 | 0.17% | 24.50% | 1,200 ms | 55.17% |

This supports asymmetric policy, not autonomous promotion: private speculation may
start permissively, but public commit must be independently conservative. The authored
state proxies improved commit safety without improving semantic prediction. They are
not evidence of a benefit from real acoustic features.

## 005b: downstream response-plan execution

The follow-up froze the 005a corpus and prediction ledger by SHA-256 and opened the
prediction SQLite database read-only. It used the selected `gemma3:4b` predictions at
the 0.50 branch threshold and `qwen3:8b` as the downstream plan generator and verifier.
Across three seeds, it generated 600 completed-turn reference plans and 1,085 private
speculative plans: 600 for transcript-only C and 485 for state-enriched D. No task,
TTS, or user-visible path was available.

The verifier graded each plan as exact, lightweight repair, partial, or unusable.
Only exact and lightweight repair were potentially reusable, and reuse additionally
required the predicted semantic endpoint to match the locked final endpoint. Latency
accounting charged speculative readiness after turn end, verification, bounded repair,
and final-turn regeneration after rejection. The report includes zero-savings
no-branch trials and reports distribution tails rather than means alone.

| Metric | C: transcript | D: state proxies |
|---|---:|---:|
| Branch start rate | 100.00% | 80.83% |
| Safe usable-plan rate | 27.33% | 35.17% |
| Mean net latency saved | -1,715 ms | -1,685 ms |
| Median net latency saved | -1,470 ms | -1,577 ms |
| Trials with positive savings | 2.00% | 1.50% |
| Mean wasted speculative generation | 1,259 ms | 821 ms |
| Judge accepted a semantically invalid branch | 8.33% | 8.17% |
| Invalid endpoint promoted after hard gate | 0.00% | 0.00% |
| Early late-reversal branch promoted | 0.00% | 0.00% |

The response-plan reuse rate alone looked encouraging, but it did not translate into
latency benefit. Verification and repair were more expensive than fresh plan creation,
and the LLM reuse judge was insufficient as a safety boundary: it accepted invalid
semantic branches in roughly eight percent of all trials. The independent semantic
endpoint gate prevented those false accepts from being promoted.

## Decision

Do not proceed to response-draft speculation under this design. It would spend more
compute on a less reusable artifact while inheriting a verifier that is not safe on
its own. Do not escalate to recorded speech or a live assistant from these results.

The experiment does support three narrower conclusions:

1. Separate private branch thresholds from public commit thresholds.
2. Require a deterministic or independently grounded semantic-validity gate before
   any speculative artifact can be reused; an LLM similarity judge is not enough.
3. If revisited, make verification substantially cheaper than baseline generation and
   speculate on a smaller, more stable intermediate representation than a full plan.

Artifacts are retained under ignored `artifacts/labnote-005/`. The detached 005b
service completed successfully with 600/600 reference plans and 1,085/1,085 branches,
zero recorded failures, and zero service restarts.
