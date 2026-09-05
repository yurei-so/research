# Experiment inventory

Inventory taken 2026-09-05 before experiment-repository imports. Source
checkouts remain authoritative until each row is migrated and verified in this
repository.

## Conversation prosody family

Source: `yurei-so/conversation-prosody-pipeline`, local branch
`experiment/labnote-004-listener-review` at `fcf8e2d`. The branch is clean but
contains one local commit not present on its upstream branch; migration must
preserve it.

| Future ID | Canonical note | Status | Outcome | Primary tags | Inventory note |
| --- | --- | --- | --- | --- | --- |
| `prosody-001` | Selected Poems real-media ingest | Complete | Positive | `conversational-prosody`, `real-audio`, `ingest` | File and simulated-stream metadata were consistent. |
| `prosody-002` | Shakespeare downstream-response pilot | Complete | Negative | `conversational-prosody`, `downstream-response`, `negative-result` | Did not demonstrate improved responses. |
| `prosody-003` | Amy-LM synthetic prosody pilot | Complete | Inconclusive | `conversational-prosody`, `synthetic-audio`, `provenance` | Source audio was later quarantined because synthesis provenance was unrecoverable. |
| `prosody-004` | Context-conditioned prosody IR | Awaiting review | Pending | `conversational-prosody`, `prosody-ir`, `human-review` | Inference and oracle synthesis completed; original listener evaluation remained pending. |
| `prosody-005` | Speculative turn prediction | Complete | Negative | `turn-taking`, `speculative-execution`, `latency`, `safety` | No downstream latency win; conservative public/private asymmetry retained. |
| `prosody-006` | Familiarity/readiness gate | Complete | Negative | `speculative-execution`, `counterfactual`, `negative-result` | Cheap gate worked mechanically but selected worse-than-average turns. |
| `prosody-007` | Bounded speculation subscriptions | Complete | Inconclusive | `speculative-execution`, `attention-subscription`, `inconclusive-result` | Mechanism worked; selection advantage was not demonstrated. |
| `prosody-008` | Audible focus-control gate | Needs reconciliation | Pending | `conversational-prosody`, `synthetic-audio`, `naturalness` | Only an experiment README exists; its status says a smooth-focus revision is pending even though later follow-ups exist. Create a canonical note and reconcile the frozen revision/result. |
| `prosody-009` | Native Kokoro stress pilot | Complete | Mixed | `conversational-prosody`, `synthetic-audio`, `blinded-review`, `mixed-result` | Naturalness passed; four-trial review did not validate intended focus mapping. Only an experiment README exists. |
| `prosody-010` | Native stress prominence gate | Complete | Negative | `conversational-prosody`, `synthetic-audio`, `negative-result` | Zero of six trials passed; no further listener labor earned. Only an experiment README exists. |
| `prosody-011` | Reproducible synthetic rerun | Complete | Inconclusive | `conversational-prosody`, `synthetic-audio`, `provenance-repair` | Provenance and fidelity gates passed; matched cues still showed no unique automatic advantage. |

## Composition family

Source: `yurei-so/composition-pipeline`, clean `dev` branch at `197ca75`.

| Future ID | Canonical note | Status | Outcome | Primary tags | Inventory note |
| --- | --- | --- | --- | --- | --- |
| `composition-001` | Prompted constrained-editing baseline | Complete | Positive | `composition`, `constrained-decoding`, `protocol` | Mechanical reliability gate passed; no writing-quality claim. |
| `composition-002` | Seeded mandatory-revision campaign | Complete | Inconclusive | `composition`, `blinded-review`, `revision` | Direct rewrite led numerically, but the small review was not decisive. |
| `composition-003` | Optional editor-access campaign | Complete | Negative | `composition`, `blinded-review`, `latency`, `negative-result` | Mostly ties, high protocol-failure rate, and no earned promotion. |
| `composition-004` | Changed-output optional-editor campaign | Complete | Inconclusive | `composition`, `blinded-review`, `deduplication` | Diagnosed deterministic pseudoreplication; raw judgments were not independent evidence. |
| `composition-005` | Stochastic deduplicated editor campaign | Complete | Negative | `composition`, `blinded-review`, `deduplication`, `negative-result` | Diversity improved, but the extra editor pass did not justify its cost. |
| `composition-006` | Targeted residual-defect repair | Complete | Mixed | `composition`, `targeted-repair`, `deduplication`, `mixed-result` | Repair mechanism worked, but diversity gates correctly withheld human review. |

## Related project classification

- `composition-review` is reusable human-review apparatus and has already been
  imported with full history under `apparatus/composition-review`.
- `prosody-demo` is not itself a numbered experiment corpus. Classify it during
  migration as either a graduated standalone demonstration referenced here or
  an experiment implementation with an explicit parent labnote.

## Migration checks

Before marking either family imported:

1. Add version-1 front matter without rewriting the scientific body.
2. Reconcile Prosody 008 and promote Prosody 009–010 experiment READMEs into
   canonical labnote documents.
3. Preserve frozen protocols, source revisions, negative results, and the local
   unpushed Prosody commit.
4. Validate IDs, controlled status/outcome values, relative links, and unique
   note identity before building Pages indexes.

