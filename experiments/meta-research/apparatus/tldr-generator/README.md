# Experimental labnote TL;DR apparatus

This is the META-RESEARCH-001 shadow-mode apparatus, not yet a supported component of
`research-tools`.

It accepts a canonical labnote plus a JSON candidate produced by any model,
adds source and apparatus provenance, and deterministically checks whether the
candidate is structurally ready for human review. A passing result is not a
factual-grounding verdict. The apparatus never edits the source note or public
site.

Version `0.2.0` targets an orientation rather than a compressed abstract. Its
entire reader-facing output is exactly two sentences:

1. `question_or_cause` says what question or causal premise motivated the note.
2. `effect` says what happened and why that result changes the reader's decision.

The two sentences may total at most 320 characters. V2 does not ask the model to
extract citations: the apparatus records a deterministic hash of the complete
source plus model and prompt provenance, and human review evaluates fidelity.
The legacy `labnote-tldr/v1` validator remains available solely to reproduce
the stopped pilot receipts.

If later activated, the orientation must be disclosed as generated and visually
separate from authored labnote prose. The experiment specifies a quiet muted
panel with clipped corners and a compact `AI ORIENTATION · EXPERIMENTAL` label;
it must remain easy to skip and must not masquerade as canonical text.

Version `0.3.0` adds the Crayon Speak register after v2 human review found that
two short sentences could still behave like a tiny abstract. V3 keeps the hard
two-sentence and provenance checks, but treats word counts, acronyms, and known
paper-language as review warnings rather than gameable hard vocabulary rules.
Human review is deliberately binary: accept when the orientation helps the
reviewer understand the note quickly, otherwise reject with a reason. V3 does
not ask the reviewer to reverse-engineer that judgment into five correlated
numeric scores.

```bash
node src/cli.mjs validate --source path/to/labnote.md --candidate candidate.json
```

Model invocation is intentionally outside the trusted validator. Providers may
be local, Runtime Roost, or API-backed, but they must emit the same candidate
contract. This keeps credentials and provider-specific behavior out of the
public research build.
