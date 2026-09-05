# Experiment labnotes

Labnotes form the chronological experimental record for Conversation Prosody
Pipeline. Each note has a stable sequential identifier and a descriptive slug:

```text
labnote-NNN-short-description.md
```

Assign the next unused number when adding a note. Numbers describe publication order,
not success or importance, and are never reused. Keep negative, inconclusive,
aborted, and design-only work in the record when it informs later experiments; state
the outcome clearly inside the note.

## Index

| ID | Run date | Question | Status | Relationship |
|---|---|---|---|---|
| [001](labnote-001-selected-poems-real-media.md) | 2026-06-27 | Do file and simulated-stream ingestion produce consistent metadata from real spoken audio? | Successful | Initial real-media ingest check |
| [002](labnote-002-shakespeare-monologue-downstream-response.md) | 2026-07-01 | Do delivery cues improve or meaningfully change an LLM's conversational response? | Failed to demonstrate improvement | Follows 001; moves from ingest consistency to downstream usefulness |
| [003](labnote-003-amy-lm-synthetic-prosody-downstream-response.md) | 2026-07-01 | Do matched cues improve responses to flattened conversational text over text-only and shuffled controls? | Negative/inconclusive; source audio quarantined | Follows 002; later audit found the third-party synthesis method unrecoverable |
| [004](labnote-004-context-conditioned-prosody-ir.md) | 2026-08-13 | Can local models infer intended prosody from discourse context, and can Kokoro render the inferred structure? | Inference and oracle synthesis complete; listener evaluation pending | Holds target wording fixed; evaluates inference and synthesis separately |
| [005](labnote-005-speculative-turn-prediction.md) | 2026-08-13 | Can semantic branch prediction hide response latency while conservative turn-state estimation avoids interruption? | Negative downstream latency result; safety asymmetry supported | Synthetic timed replay; draft and real-audio escalation not earned |
| [006](labnote-006-familiarity-readiness-gate.md) | 2026-08-15 | Can earned conversational familiarity cheaply gate speculation to turns with positive net value? | Gate failed; oracle opportunity remains | Microsecond gate reduced waste but selected worse-than-average turns |
| [007](labnote-007-bounded-speculation-subscriptions.md) | 2026-08-15 | Can an LLM request bounded attention subscriptions for predictable conversational trajectories? | Mechanism worked; selection advantage not demonstrated | Semantic continuity did not reliably predict reusable speculative work |
| [011](labnote-011-reproducible-synthetic-rerun.md) | 2026-08-23 | Does Labnote 003 persist with locally generated, fidelity-gated audio? | Completed; automatic result negative/inconclusive | Provenance repair and both gates passed; matched cues still did not show a unique automatic advantage |
