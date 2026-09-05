# Labnote 003: Optional editor-access campaign

Date: 2026-08-23

## Hypothesis

Giving a model optional access to constrained revision after a matched direct
rewrite may improve judged output without forcing a mutation. Finalizing the
initial candidate unchanged is a first-class treatment outcome.

## Frozen protocol

- Experiment: `labnote_003`
- Agent Runtime run: `9e55ef72-4817-4b2a-b07f-b51102e425aa`
- Campaign digest: `6728008926b7d896ced277199b03748c3beda1400a0ea1a152a6dd8f879fadd3`
- Repository revisions: `9a57f28`, corrected by `fd4c02f`
- Model: `qwen3:8b`
- Arms: matched direct rewrite and optional editor access
- Planned trials: 48
- Blinded pairs: 24
- Accelerator ownership: one non-preemptive roostd experiment lease

The optional arm receives the same deterministic initial rewrite as its matched
direct arm, followed by one editor decision. It may finalize unchanged or apply
bounded revision operations. Invalid editor output is recorded as a protocol
failure and transactionally falls back to the unchanged initial candidate, so
failure cannot selectively remove a difficult case from human review.

Raw prompts, drafts, generated texts, editor operations, telemetry, review
pairs, and the arm-reveal key remain in owner-only private state.

## Runtime result

The authoritative campaign completed all 48 trials successfully at the
execution layer and released its accelerator lease normally.

| Arm | Completed | Protocol success | Transactional fallback |
| --- | ---: | ---: | ---: |
| Direct rewrite | 24 | 24/24 | 0 |
| Optional editor access | 24 | 12/24 | 12 |

All 24 matched comparisons remain in the blinded review set. The public review
bundle digest is
`534755a72c09fcc375f580bb0afbb36bd6801b8db35a575ea1371c999fdd6f8e`.

The original pilot retained only valid optional-editor trials and would have
created survivor bias. It is preserved as diagnostic evidence but is not an
inferential campaign. The authoritative rerun uses the frozen
`transactional-fallback-v1` protocol revision.

## Blinded human review result

The owner completed all 24 locked judgments on 2026-08-23. The reveal gate
opened only after the final judgment was durably committed against the original
bundle digest.

| Preferred arm | Pairs | Share of all pairs |
| --- | ---: | ---: |
| Direct rewrite | 0 | 0% |
| Optional editor access | 2 | 8.3% |
| Tie | 22 | 91.7% |

Both non-ties preferred optional editor access, but an exact two-sided binomial
test on only two non-ties gives `p = 0.5`. This is not evidence of an arm-level
quality advantage. Both preferences occurred among the four voluntarily edited
cases; the other two edited cases tied. All eight valid unchanged decisions and
all twelve transactional fallbacks tied. No secondary-dimension scores were
recorded.

The treatment voluntarily edited 4/12 protocol-valid cases (33.3%), or 4/24 of
all treatment assignments (16.7%). Eight valid cases finalized unchanged and
twelve invalid editor responses used the frozen unchanged fallback. The valid
edits contained six replacements and two deletions in aggregate.

| Arm | Mean generated tokens | Mean prompt tokens | Mean latency | Generations |
| --- | ---: | ---: | ---: | ---: |
| Direct rewrite | 33.75 | 91.00 | 0.593 s | 1 |
| Optional editor access | 98.75 | 319.75 | 1.584 s | 2 |

Optional access therefore used about 2.9 times the generated tokens, 3.5 times
the prompt tokens, and 2.7 times the latency of direct rewrite in this campaign.
Candidate text, operations, pair-level judgments, and treatment assignments
remain in owner-only private state and are not reproduced here.

## Disposition

- Do not fine-tune or promote optional editor access from this result.
- Treat the overwhelming tie rate as the primary finding: matched deterministic
  outputs were usually unchanged or judged equivalent.
- The two optional-editor preferences are localized to one case/style cell and
  are too few for a general conclusion.
- Repair the 50% editor-protocol failure rate before another quality campaign.
- If optional editing is revisited, target tasks with a measurable residual
  defect after direct rewrite and require the planned secondary scores.
- Preserve zero edits and transactional fallback as first-class outcomes; do
  not filter either from future review.
