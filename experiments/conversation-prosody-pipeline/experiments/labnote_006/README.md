# Labnote 006 familiarity/readiness gate

**Status:** Complete. The gate met its microsecond cost budget but selected held-out
turns worse than the population and did not earn recorded or live escalation.

This experiment tests whether a tiny readiness policy can select the minority of
unfinished turns where private speculative response work has positive net value.
The gate makes no model, embedding, retrieval, network, or database call. It scores
seven cached/current numeric features with logistic regression and updates session
statistics in constant time.

The counterfactual runner executes every branch offline so all policies see identical
outcomes. The analyzer fits thresholds on 30 complete sessions and evaluates once on
10 held-out sessions. Drafts, tools, TTS, and public output are out of scope.
