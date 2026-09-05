# Lab note: Familiarity-gated speculative cognition

**Run date:** 2026-08-15

**Status:** Complete; opportunity exists, but the lightweight readiness gate failed

**Execution host:** `mpaiServer-8kl`

## Question

Can a runtime use a sub-millisecond readiness policy to select the minority of
unfinished conversational turns where private speculative response work has positive
net value, while abstaining everywhere else?

## Motivation

Labnote 005b found that broadly enabled response-plan speculation lost roughly 1.7
seconds after verification and fallback costs. Plausible reuse was not sufficient.
This follow-up tests whether predictability is relational and earned through relevant
conversation history rather than globally available on every turn.

## Lightweight gate contract

The readiness gate receives seven numeric values already present in session or
turn-state processing: bounded history depth, smoothed historical endpoint precision,
recent topic stability, recent endpoint validity, current endpoint confidence, current
turn-end confidence, and available head start. It is logistic regression: one frozen
dot product and sigmoid.

The gate performs:

- no additional model or GPU inference;
- no embedding or semantic retrieval;
- no network or database access;
- no transcript-history scan; and
- constant-time updates to a bounded session record.

Measured scoring time is reported and must remain below 1 ms median and 2 ms p99 to be
operationally interesting. Missing or malformed state fails closed.

## Corpus and split

The authored synthetic corpus contains 40 multi-turn sessions of 25 turns each. Thirty
sessions are used for model/threshold development and ten complete sessions remain
held out. Ten sessions intentionally change topic frequently; the remainder contain
stable blocks with controlled topic changes. Each session cycles through direct,
implicit, hesitation, late-reversal, and collaborative-completion turns.

For each of 1,000 turns and two seeds, the counterfactual collector records an early
semantic endpoint prediction, a private early response skeleton, and a response
skeleton generated from the locked final turn. Work is batched by model to avoid
irrelevant model-loading overhead. The 1,300 ms authored head start matches the prior
timed replay scale.

The response skeleton is intentionally smaller than the 005b plan: one response move
and one strategy selected from finite enums. Reuse requires both an independently
correct final semantic endpoint and an identical final-turn skeleton. No LLM reuse
judge is a safety boundary.

## Policies

| ID | Policy | Role |
|---|---|---|
| A | Never speculate | Zero-cost latency baseline |
| B | Always speculate | Broad-speculation control |
| C | Enable after a tuned message count | Naive familiarity baseline |
| D | Current endpoint confidence threshold | History-free confidence baseline |
| E | Lightweight familiarity/readiness score | Proposed policy |
| F | Oracle selects only positive counterfactuals | Upper bound on gateable value |

C, D, and E select their threshold using development sessions only. Their frozen
thresholds are evaluated once on the ten held-out sessions. The offline collector runs
all branches only to expose counterfactual outcomes; a deployed gate would execute
only selected rows.

## Metrics and decision rule

Primary metrics are held-out coverage, mean/median/total net milliseconds saved, safe
reuse rate among selected turns, wasted speculative compute, gate execution time, and
invalid endpoint promotions. Net latency charges any speculative work finishing after
true turn end; rejected work cannot be promoted. Predictor cost is part of the shared
turn-state path rather than an extra readiness-gate call.

The readiness design earns a recorded replay only if it has zero invalid promotions,
positive held-out mean and median net latency, materially beats always-on and the
message-count baseline, reduces wasted compute by at least 70% from always-on, and
stays within the CPU gate budget. Draft speculation and the separate live voice demo
remain out of scope until those conditions are met.

## Results

The detached run completed 2,000/2,000 counterfactual rows with zero failures and zero
service restarts. Thresholds were selected on 1,500 rows from the 30 development
sessions and applied once to 500 rows from ten held-out sessions. The held-out endpoint
accuracy was 57.40%; 16.40% of rows produced a safely reusable and latency-positive
skeleton.

| Policy | Coverage | Safe reuse among selected | Mean saved per held-out turn | Selected median | Wasted compute |
|---|---:|---:|---:|---:|---:|
| A: never | 0.00% | n/a | 0 ms | n/a | 0 ms |
| B: always | 100.00% | 16.40% | 125 ms | 0 ms | 323,937 ms |
| C: after 5 turns | 80.00% | 17.75% | 109 ms | 0 ms | 256,881 ms |
| D: confidence >= 0.60 | 100.00% | 16.40% | 125 ms | 0 ms | 323,937 ms |
| E: readiness >= 0.30 | 5.60% | 7.14% | 3 ms | 0 ms | 20,153 ms |
| F: oracle | 16.40% | 100.00% | 125 ms | 760 ms | 0 ms |

The gate remained operationally negligible: 1.37 microseconds mean and 1.66
microseconds p99 on the analysis host. It reduced wasted compute by 93.78% relative to
always-on, but mostly by abstaining. Its selected turns were less reusable than the
population, and it recovered only 1,628 ms total versus 62,683 ms for always-on and the
oracle. It failed the preregistered requirement to outperform always-on and the naive
message-count policy.

The smaller skeleton changed the latency economics from 005b. Speculative generation
usually completed inside the 1,300 ms head start, so rejected branches added no
post-turn latency even while wasting GPU work. Always-on therefore had positive mean
latency but zero median benefit and spent 387,316 ms total speculative compute to
recover 62,683 ms of latency.

Held-out diagnostics did not show monotonic familiarity:

- turns 0–4: 11.00% reusable;
- turns 5–14: 20.00% reusable;
- turns 15–24: 15.50% reusable;
- stable sessions: 18.00% reusable;
- unstable sessions: 12.67% reusable; and
- late-reversal turns: 0.00% reusable and zero promotions.

The oracle remains informative. A perfect selector could cover 16.40% of turns and
save a median 760 ms on selected turns with no wasted compute. The speculative
skeleton therefore contains recoverable value, but these cheap familiarity features
did not identify it reliably on held-out conversations.

## Decision

Do not advance this readiness gate to recorded speech or the separate live demo. Do
not respond by adding a larger gate model, retrieval, embeddings, or more runtime
machinery: that would violate the purpose of the experiment and risk moving 005b's
overhead into the selector. The useful result is narrower: relational/topic stability
contains some signal and an oracle opportunity exists, but message count and the
current compact readiness score are not adequate selectors.

Any future revisit should begin with a different already-available signal or a much
cheaper rule demonstrated retrospectively on new held-out sessions. It should not
increase gate complexity merely to fit this corpus.
