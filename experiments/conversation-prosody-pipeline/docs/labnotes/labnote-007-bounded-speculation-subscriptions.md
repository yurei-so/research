# Lab note: LLM-directed bounded speculation subscriptions

**Run date:** 2026-08-15

**Status:** Complete; operational mechanism worked, selection advantage was not demonstrated

**Execution host:** `mpaiServer-8kl`

## Question

Can a conversational model recognize a predictable semantic trajectory once per
completed turn and request a bounded runtime-owned subscription that selects future
speculative work more effectively than a stateless numeric readiness gate?

## Motivation

Labnote 006 found a real oracle opportunity but its seven-feature logistic readiness
gate selected worse-than-average turns. This follow-up changes the decision unit from
one partial turn to a short conversational trajectory. The LLM may request that the
runtime watch the next one to three turns; it cannot itself start inference, publish
output, speak, invoke tools, or extend authority.

The runtime owns TTL, topic-scope matching, local confidence, and cancellation. A
topic mismatch, TTL exhaustion, or one speculative miss closes the subscription.
Public commit remains independently gated.

## Cheap structural gate

Before any new model calls, a CPU-only analysis tested whether profitable 006 outcomes
clustered. Development would proceed if lag-one profitable-turn lift was at least 1.5
over base rate or at least 25% of profitable turns occurred in runs of two or more.

On 1,500 development rows, 42.12% of profitable turns occurred in runs of at least
two, including 41 two-turn and 11 three-turn runs. The structural gate therefore
passed. The sealed 500-row held-out split was not inspected at this stage.

## Selector protocol

After each completed turn except the final turn in a session, `qwen3:8b` received at
most the previous six completed user turns. It returned a finite schema:

```json
{
  "subscribe": true,
  "ttl_turns": 2,
  "topic_scope": "software",
  "reason": "The user is continuing one deployment diagnosis"
}
```

The request applies only to future turns. It cannot see the next partial turn or any
future outcome. Runtime simulation then applies the subscription to the frozen
Labnote 006 counterfactual ledger; no speculative skeleton was regenerated.

The development collector completed 1,440 decisions across 30 sessions and two seeds.
The runtime tested local confidence thresholds 0.0, 0.7, 0.8, and 0.9. The frozen
selection rule maximized development latency recovery subject to reducing wasted
compute by at least 70% relative to always-on. Threshold 0.0 won; thresholds through
0.8 were behaviorally identical because predictor confidence was saturated, while
0.9 selected no reusable work. This freeze was recorded before the 480 held-out
selector decisions were generated.

## Results

Both detached selector runs completed every task with zero failures and zero service
restarts.

| Metric | Development | Held out |
|---|---:|---:|
| Selector decisions | 1,440 | 480 |
| Subscription requests | 449 | 140 |
| Runtime coverage | 22.07% | 19.20% |
| Safe reuse among selected | 9.97% | 17.71% |
| Mean latency saved per corpus turn | 16.75 ms | 24.30 ms |
| Total latency recovered | 25,123 ms | 12,151 ms |
| Total speculative compute | 261,890 ms | 74,456 ms |
| Wasted speculative compute | 236,317 ms | 61,604 ms |
| Invalid promotions | 0 | 0 |

Held-out subscription selection reduced wasted compute by 80.98% relative to
always-on, but it also recovered only 19.39% of the oracle/always-on latency. The
changes were nearly proportional. Latency recovered per millisecond of speculative
compute was approximately:

- subscription: 0.163;
- always-on: 0.162; and
- naive speculation after five turns: 0.175.

The subscription therefore did not materially enrich profitable work. Its held-out
safe-reuse rate of 17.71% was only modestly above the 16.40% population rate and below
the naive five-turn policy's 17.75%.

The structural premise also weakened on held-out data. Profitable-turn lag-one lift
fell from 1.29 on development to 0.84 held out: a profitable turn was followed by
another profitable turn only 13.75% of the time, below the 16.40% base rate. The share
of profitable turns in runs of two or more fell from 42.12% to 21.95%. Development's
apparent clustering did not generalize.

## Interpretation

The runtime mechanism behaved correctly. TTL and topic scope bounded attention,
single misses canceled subscriptions, and no invalid branch was promoted. It also
substantially reduced absolute GPU waste and recovered more latency than Labnote 006's
stateless readiness gate.

However, the conversational LLM appears to recognize semantic continuity rather than
the narrower property needed here: whether an unfinished future turn will produce a
reusable response skeleton. Coherent conversational momentum was not a sufficiently
selective proxy for profitable speculative computation.

This distinction is the central result:

> A conversation can be predictably about the same thing without its next partial
> utterance supporting reusable downstream response work.

## Decision

Do not advance this subscription selector to recorded speech or the separate live
voice demo. Do not add retrieval, embeddings, a larger selector, or more elaborate
subscription state merely to fit these sessions. The bounded runtime primitive remains
a sound architectural option for other attention tasks, but this experiment did not
demonstrate a meaningful selection advantage for speculative response skeletons.

Artifacts are retained under ignored `artifacts/labnote-007/`. The repository records
the frozen protocol, selector runner, runtime simulator, structural analysis, service
definitions, and focused tests; generated model ledgers remain out of Git.
