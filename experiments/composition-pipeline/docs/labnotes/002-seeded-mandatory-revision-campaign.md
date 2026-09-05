# Labnote 002: Seeded mandatory-revision campaign

Date: 2026-08-22

## Hypothesis

Schema-constrained revision can reliably transform a seeded draft through real
virtual-buffer mutations and produce outputs suitable for blinded comparison
with direct rewriting.

## Frozen protocol

- Experiment: `labnote_002`
- Agent Runtime run: `a7561073-8304-40d7-930b-33b1cd8b551e`
- Campaign digest: `e1dd20cac2d419017ebea302e47f4ea9ef06ac672c802f075bfa613183efd490`
- Repository revision: `152f4a3`
- Model: `qwen3:8b`
- Cases: six reviewed seeded drafts with known defects
- Arms: direct rewrite and schema-constrained mandatory revision
- Prompt styles: concise and preservation-first
- Repetitions: two
- Planned trials: 48
- Accelerator ownership: one non-preemptive roostd experiment lease

The committed manifest, protocol, and corpus are the authoritative inputs. Raw
prompts, drafts, generated texts, checkpoints, review pairs, and the arm-reveal
key remain in owner-only private state and are not reproduced here.

## Runtime result

The campaign completed all 48 trials successfully at the infrastructure level
in approximately 43 seconds. It exited 0, produced an empty stderr log, released
its accelerator lease normally, and left the queue idle and unblocked.

| Arm | Completed | Protocol success | Mean draft similarity | Mean generated tokens | Mean latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| Direct rewrite | 24 | 24/24 (100%) | 0.424 | 34.3 | 0.69 s |
| Schema revision | 24 | 22/24 (91.7%) | 0.587 | 73.0 | 1.09 s |

The 22 applicable schema-revision trials averaged 2.09 real revision operations.
This closes Labnote 001's zero-edit limitation: the model exercised seeded-buffer
mutations rather than supplying only a final replacement.

Both protocol failures occurred in the same matrix cell:
`bounded-safeguards` with the `preservation_first` prompt style. Each produced a
parseable operation document but omitted finalization. No retry-level campaign
failure or infrastructure stop condition occurred.

## Blinded review material

The runner created 22 deterministic A/B pairs and a separate reveal key. The
public experiment result contains only the pair count and bundle digest:
`8abd30015163779d812487bfbe2d4201c1037e397acab2c3cc5414540a950b30`.

Mechanical measurements do not establish which arm writes better. Draft
similarity suggests that constrained revision preserved more source material,
but whether that preservation was appropriate must be decided through blinded
human scoring.

## Blinded human review result

The owner completed all 22 locked judgments on 2026-08-23. The reveal gate
opened only after the final judgment was durably committed against the original
bundle digest.

| Preferred arm | Pairs | Share of all pairs |
| --- | ---: | ---: |
| Direct rewrite | 13 | 59.1% |
| Schema revision | 6 | 27.3% |
| Tie | 3 | 13.6% |

Among the 19 non-ties, direct rewrite was preferred in 68.4% of comparisons.
An exact two-sided binomial test against equal preference gives `p = 0.167`, so
this small review does not establish a statistically decisive arm advantage.
No secondary-dimension scores were collected. Candidate text, pair-level
judgments, and treatment assignments remain in owner-only private state and are
not reproduced here.

## Disposition

- Do not fine-tune.
- Treat mandatory seeded revision as mechanically demonstrated, but below the
  desired 95% protocol-success threshold.
- Investigate the narrow preservation-first/finalization interaction before
  expanding the corpus.
- The sanitized blinded-review workflow and all 22 judgments are complete.
- Do not select schema revision as the default composition protocol from this
  campaign. Direct rewrite led numerically, but the sample is not decisive.
- Before a broader confirmation campaign, repair the preservation-first
  finalization failure and require the planned secondary-dimension scores so a
  future review can distinguish overall preference from adherence, correctness,
  concision, voice preservation, and unintended changes.
