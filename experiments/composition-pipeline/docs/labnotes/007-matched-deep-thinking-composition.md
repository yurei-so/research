---
schema_version: 1
id: composition-007
title: "Matched deep-thinking composition campaign"
date: 2026-09-12
status: complete
outcome: negative
question: "Does enabling extended model thinking improve bounded composition enough to justify its latency and generation overhead?"
tags: ["blinded-review","composition","negative-result","reasoning-budget"]
lineage: ["composition-006"]
relations: [{"target":"composition-006","type":"reuses-data","rationale":"Reuses its twelve public rewrite tasks to isolate reasoning mode from corpus and model changes."}]
publish: true
---
# Labnote 007: Matched deep-thinking composition campaign

## Question

Does enabling extended model thinking improve bounded composition enough to justify its
latency and generation overhead?

## Frozen protocol

- Model: `qwen3:8b`, matching Composition 001–006.
- Twelve bounded rewrite tasks reused from Composition 006.
- One thinking-disabled and one thinking-enabled generation per task.
- Identical prompt, draft, model, seed, temperature, final-output contract, 4,096-token
  ceiling, and ten-minute timeout between paired arms.
- Raw prompts, outputs, thinking traces, checkpoints, and mappings remain owner-private.
- Exact output matches become automatic ties.
- Blind human review opens only with at least eight changed pairs and never exposes the
  thinking trace.

The decision boundary was preference strong enough to justify measured latency and token
overhead, not merely evidence that thinking changes the output.

## Result

All 24 generations completed without failure. Thinking-disabled calls averaged 0.741
seconds and 30.25 generated tokens. Thinking-enabled calls averaged 6.146 seconds and
501 generated tokens, corresponding to approximately 8.3 times the latency and 16.6
times the generation. Thinking-enabled responses contained an average of 2,335.75
thinking characters; their final answers were only 12.5% longer on average.

Two of twelve pairs produced exactly identical final answers and were locked as automatic
ties. The remaining ten changed pairs passed the frozen intake gate and entered blind
review. Thinking-enabled outputs won five judgments, thinking-disabled outputs won four,
and one was tied. Across all twelve tasks, the disposition was therefore five wins for
thinking, four for no thinking, and three ties.

This is a negative result for extended thinking in this bounded rewrite setting. The
treatment frequently changed the answer but did not establish a meaningful preference
advantage, while imposing substantial latency and token overhead. The run does not show
that reasoning is generally unhelpful: it used one 8B model, concise operator-facing
rewrites, one generation per arm and task, and one reviewer. Future work should test a
materially harder composition regime rather than increase reasoning effort on the same
short rewrite corpus.

