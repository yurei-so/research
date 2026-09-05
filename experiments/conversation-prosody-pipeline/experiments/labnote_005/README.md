# Labnote 005 speculative turn prediction

**Status:** Complete. Plan speculation produced negative net latency and did not earn
draft speculation or real-audio escalation.

This experiment replays 200 authored, timed turns incrementally. It evaluates whether
semantic endpoint predictions become reusable before a turn ends and whether
transcript-plus-turn-state features reduce premature commits relative to fixed silence.

The first corpus is synthetic and contains no audio. Its acoustic fields are authored
turn-state proxies (speech activity, silence, and finality), not measured acoustics.
This isolates policy and semantic-branch behavior before a recorded-speech study.

Conditions:

| ID | Turn detector | Branch input | Speculative work |
|---|---|---|---|
| A | Fixed silence | None | None |
| B | Multimodal proxy | None | None |
| C | Multimodal proxy | Transcript | Response plan |
| D | Multimodal proxy | Transcript + turn state | Response plan |
| E | Multimodal proxy | Transcript + turn state | Plan + draft |

Generated ledgers and exports belong under ignored `artifacts/labnote-005/`.

`run_downstream.py` consumes the 005a corpus and ledger in SQLite read-only mode. It
records their SHA-256 hashes, creates private structured response plans at the first
eligible C/D branch, and validates those plans only after the completed turn is known.
Reuse grades are `exact`, `lightweight_repair`, `partial`, and `unusable`. Only the
first two count as reusable. The analyzer charges verification and repair against
latency savings and records wasted speculative compute. Draft execution (E) remains
gated on positive plan-level results.
