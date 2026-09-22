# Experiment inventory

Inventory taken 2026-09-05 and expanded during full-history imports. Source
checkouts remain operationally authoritative until each imported suite is
verified and the source repository is explicitly archived.

## Meta Research family

Meta Research studies apparatus, representations, and workflows used to
produce, preserve, evaluate, discover, and communicate Yūrei research.

| ID | Canonical note | Status | Outcome | Primary tags | Inventory note |
| --- | --- | --- | --- | --- | --- |
| `meta-research-001` | Grounded build-time labnote summarization | Running | Pending | `meta-research`, `summarization`, `apparatus`, `human-review` | Shadow-mode campaign; generated candidates cannot modify the public site. Toolkit promotion and public activation are separate evidence-gated decisions. |

## Conversation prosody family

Source: `yurei-so/conversation-prosody-pipeline`, local branch
`experiment/labnote-004-listener-review` at `fcf8e2d`. The branch is clean but
formerly contained one local-only commit. It was pushed upstream as `fcf8e2d`
before migration and is preserved in the imported history.

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

## Zenith Vision family

Source: `yurei-so/zenith-vision`, clean `dev` branch at `fc011d0`. This is an
experiment-first perception repository rather than the live Zenith product;
Zenith App retains ownership of production telemetry and UI behavior.

| Future IDs | Count | Status | Outcome summary | Primary tags | Inventory note |
| --- | ---: | --- | --- | --- | --- |
| `zenith-001`–`zenith-017` | 17 | Complete | 5 positive, 4 mixed, 8 negative | `guild-wars-2`, `computer-vision`, `privacy`, `holdout`, `panel-recognition` | Preserves the full progression from conservative crop geometry through frozen holdouts, localized transfer, environment-confounding failures, and the final decision to end the frozen-backbone classifier branch. |

The final Labnote 017 result is especially important provenance: repeated
fresh holdouts exposed environment-specific Hero failures, so the branch ended
rather than spending more operator attention or tuning against spent holdouts.

## Related project classification

- `composition-review` is reusable human-review apparatus and has already been
  imported with full history under `apparatus/composition-review`.
- `prosody-demo` is not itself a numbered experiment corpus. It is imported as
  a research-derived runnable demonstration under `demos/prosody-demo`; it must
  continue pointing back to the Prosody evidence that bounds its claims.

## Voxel Guidance family

Infrastructure: `yurei-so/prism-toolkit`, local branch
`feat/owned-instance-boundary` at `bb1aa2a`. Prism Toolkit is a standalone
launcher-control dependency; experimental protocols and evidence remain here.

| ID | Canonical note | Status | Outcome | Primary tags | Inventory note |
| --- | --- | --- | --- | --- | --- |
| `voxel-guidance-001` | Minecraft behavioral-vector pilot | Complete | Mixed | `minecraft`, `behavioral-telemetry`, `repeated-measures`, `human-in-the-loop` | Twelve accepted sessions produced the frozen aggregate fingerprint; interpretation remains protocol-bound and single-participant. |
| `voxel-guidance-002` | Blinded current-task inference | Complete | Positive | `minecraft`, `behavioral-telemetry`, `classification`, `grouped-validation` | Held-seed accuracy peaked at 10/12 after 120–240 seconds; 60–240 second results survived correction across five horizons. |
| `voxel-guidance-003` | Current-task feature-family ablation | Complete | Mixed | `minecraft`, `behavioral-telemetry`, `classification`, `ablation` | Block actions alone matched the full 10/12 result; movement retained signal while inventory alone did not reliably beat chance. |
| `voxel-guidance-004` | Machine-native state serialization baseline | Complete | Mixed | `behavioral-telemetry`, `machine-native-state`, `serialization`, `apparatus` | Compact state was lossless and smaller; one exploratory local-model probe favored compact 5/12 over prose 3/12 and JSON 2/12, but is too small and post hoc to establish a reasoning advantage. |
| `voxel-guidance-005` | Semantic namespace token ablation | Complete | Negative | `machine-native-state`, `namespace`, `ablation`, `local-model` | Namespace-only exactly matched the opaque control at 3/12; the full field dictionary reached 7/12, so a readable namespace did not replace explicit field semantics. |

## Migration checks

Before marking either family imported:

1. Add version-1 front matter without rewriting the scientific body.
2. Reconcile Prosody 008 and promote Prosody 009–010 experiment READMEs into
   canonical labnote documents.
3. Preserve frozen protocols, source revisions, negative results, and the local
   unpushed Prosody commit.
4. Validate IDs, controlled status/outcome values, relative links, and unique
   note identity before building Pages indexes.
