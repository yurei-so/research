# Labnote 006: Targeted residual-defect repair

Date: 2026-08-23

## Hypothesis

A second model pass may justify its cost when restricted to repairing one
explicit residual defect in an otherwise complete direct rewrite, even though
unrestricted optional editing showed no preference advantage in Labnote 005.

## Frozen protocol

- Model: `qwen3:8b`.
- Temperature: 0.35 for baseline diversity; diagnosis, repair, and verification
  are deterministic.
- Corpus: 12 task families, two prompt styles, five repetitions (120 trials).
- Frozen defect taxonomy: omission, unsupported addition, instruction
  violation, awkward structure, tone mismatch, ambiguity, redundancy, or none.
- A diagnosis names one primary defect and anchors non-omission evidence to an
  exact candidate substring.
- Repair returns one bounded complete buffer which the controller applies as an
  exact whole-buffer replacement, and it must make at least one change.
- An independent pass must confirm the defect was fixed without regression.
- Unchanged and duplicate pairs are excluded before review.
- Human review opens only with 12 unique verified pairs across six task families.

Raw prompts, candidates, evidence, operations, hashes, and mappings remain in
owner-only state. Public output contains only aggregate campaign telemetry.

## Status

Protocol v4 is frozen and awaiting its coordinated Agent Runtime / roostd run.

The initial v1 execution completed 120/120 trials with no scheduler failures,
but is invalid for scientific interpretation. It diagnosed 40 residual defects
and then rejected every repair document at the edit-protocol boundary (29
missing finalization operations, 10 invalid delete shapes, and one invalid
replace shape). No repair was applied and no review opened. Version 2 replaces
the unnecessarily expressive edit document with one bounded complete buffer
that the controller applies as an exact whole-buffer replacement. The v1 state
remains preserved and v2 uses a fresh state directory and campaign digest.

The v2 replacement then halted safely after 24 trials because seven transient
`OllamaError` failures exceeded the precommitted 15% failure-rate ceiling.
Ollama remained active with zero service restarts and its API stayed healthy.
No repair reached verification and no review opened, so v2 is also invalid for
scientific interpretation. Version 3 keeps the same trial and review budgets
but permits four bounded retries per trial and again uses a fresh state path and
campaign digest.

Version 3 reproduced the same seven deterministic failures after five attempts
each. Mapping only public trial parameters showed that every failure occurred
on a case that reached the replacement-generation call, while `none` diagnoses
completed. The structured replacement schema itself was therefore the failing
boundary. Version 4 removes structured output from only that call: the model
returns the repaired buffer directly, and the controller enforces nonempty and
16,000-character bounds before applying one exact replacement. It uses another
fresh state path and digest; v1-v3 remain preserved as invalid engineering runs.

## Valid v4 result

- Agent Runtime run: `f0b19d63-c1e3-4495-a09c-b27bee488b6f`
- Repository revision: `c99911c`
- Campaign digest: `3eab95852212330f60f5179c2978d982de5f844549a3dd10f4bedad95e1df98d`
- Completed: 120/120 with zero failed trials, empty stderr, and clean lease release.
- Diagnoses: 80 none, 28 redundancy, 10 tone mismatch, one omission, and
  one instruction violation.
- Repairs attempted: 40.
- Changed and independently verified repairs: 33.
- Unique verified unordered answer pairs: 11.
- Duplicate verified occurrences excluded: 22.
- Eligible task families: five.
- Frozen intake requirement: 12 unique pairs across six task families.
- Gate result: failed; zero pairs were released to human review.
- Private review-bundle digest:
  `c119293b711dcf5ab99d4ffe9bf3fa34f6555c9982f5dc527120fb736b5fc94a`.

## Disposition

The narrow repair mechanism is operationally viable: 33 repairs survived an
independent defect/regression check with no campaign failures. The study did
not earn human review, however, because the evidence concentrated in repeated
redundancy and tone fixes and collapsed below both precommitted diversity
thresholds after exact-pair deduplication. Do not lower the gate after seeing
the result. A future campaign must introduce genuinely broader residual-defect
opportunities rather than repeat or temperature-scale this corpus. Preserve
the direct-buffer repair contract, independent verification, deduplication,
and task-family coverage gate as reusable infrastructure.
