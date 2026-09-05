# Labnote 007 bounded speculation subscriptions

**Status:** Complete. Bounded subscriptions worked operationally but did not materially
enrich profitable held-out turns over always-on or the naive message-count baseline.

This follow-up tests whether profitable Labnote 006 counterfactuals cluster into
bounded conversational windows before spending GPU time on an LLM-directed attention
selector. Development sessions pass the structural gate if lag-one profitable-turn
lift is at least 1.50 over base rate or at least 25% of profitable turns occur in runs
of two or more. Held-out structure remains unread until the selector protocol is
frozen, if the development gate passes.

Development passed through clustered-positive share: 42.12% of profitable turns were
in runs of at least two. The selector makes one bounded semantic decision after each
completed turn, using at most the last six completed user turns. It cannot see the
current partial turn or future outcomes. Runtime simulation owns TTL, topic-scope,
confidence, miss cancellation, and all speculative effects.

Development selected confidence threshold 0.0 under the preregistered rule: it was the
highest-latency configuration meeting at least 70% wasted-compute reduction. Thresholds
0.0 through 0.8 were behaviorally identical because predictor confidence was saturated;
0.9 selected no reusable work. This freeze is recorded before held-out selector calls.

Held-out evaluation completed 480/480 decisions. Subscription coverage was 19.20%,
safe reuse among selected turns was 17.71%, and invalid promotions remained zero.
Waste fell about 81% from always-on, but recovered latency fell by nearly the same
proportion; latency per speculative-compute millisecond did not improve materially.
