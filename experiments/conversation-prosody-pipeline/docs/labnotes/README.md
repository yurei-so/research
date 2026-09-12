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
| [004](labnote-004-context-conditioned-prosody-ir.md) | 2026-08-13 | Can local models infer intended prosody from discourse context, and can Kokoro render the inferred structure? | Inference was mixed; 11-pair listener evaluation was inconclusive | Holds target wording fixed; evaluates inference and synthesis separately |
| [005](labnote-005-speculative-turn-prediction.md) | 2026-08-13 | Can semantic branch prediction hide response latency while conservative turn-state estimation avoids interruption? | Negative downstream latency result; safety asymmetry supported | Synthetic timed replay; draft and real-audio escalation not earned |
| [006](labnote-006-familiarity-readiness-gate.md) | 2026-08-15 | Can earned conversational familiarity cheaply gate speculation to turns with positive net value? | Gate failed; oracle opportunity remains | Microsecond gate reduced waste but selected worse-than-average turns |
| [007](labnote-007-bounded-speculation-subscriptions.md) | 2026-08-15 | Can an LLM request bounded attention subscriptions for predictable conversational trajectories? | Mechanism worked; selection advantage not demonstrated | Semantic continuity did not reliably predict reusable speculative work |
| [008](labnote-008-audible-focus-control-gate.md) | 2026-08-23 | Can post-hoc focus control create audible, natural emphasis before spending human-review labor? | Negative; v3 passed acoustic metrics but retained an obvious voice artifact | Follows 004; stopped before judgments and motivated native synthesis in 009 |
| [009](labnote-009-native-kokoro-stress-pilot.md) | 2026-08-23 | Can native Kokoro lexical stress produce natural audio and validate the intended focus mapping? | Naturalness passed; focus mapping not validated | Follows 008; removes post-hoc DSP artifacts |
| [010](labnote-010-native-stress-prominence-gate.md) | 2026-08-23 | Does native lexical stress create reliable directional discourse prominence? | Complete negative result | Follows 009; automatic gate ended this mechanism before more listener labor |
| [011](labnote-011-reproducible-synthetic-rerun.md) | 2026-08-23 | Does Labnote 003 persist with locally generated, fidelity-gated audio? | Completed; automatic result negative/inconclusive | Provenance repair and both gates passed; matched cues still did not show a unique automatic advantage |
| [012](labnote-012-reference-conditioned-focus-transfer.md) | 2026-09-11 | Can whole-utterance reference conditioning reproduce explicitly demonstrated contrastive focus? | Complete negative result | Eight valid F5-TTS outputs failed the naturalness admission gate before directional or blinded review |
| [013](labnote-013-qwen-instruction-focus-pilot.md) | 2026-09-11 | Can reference-free instructions produce natural, directionally correct contrastive focus? | Complete negative result | Qwen cleared naturalness but placed emphasis incorrectly under the paired instruction template |
| [014](labnote-014-instruction-form-ablation.md) | 2026-09-11 | Does removing the competing focus word restore directional contrastive emphasis? | Planned eight-output ablation | Compares positive-only and context-only instructions under one shared Qwen seed |
