# Experimental labnote TL;DR apparatus

This is the META-RESEARCH-001 shadow-mode apparatus, not yet a supported component of
`research-tools`.

It accepts a canonical labnote plus a JSON candidate produced by any model,
adds source and apparatus provenance, and deterministically checks whether the
candidate is structurally ready for human review. A passing result is not a
factual-grounding verdict. The apparatus never edits the source note or public
site.

```bash
node src/cli.mjs validate --source path/to/labnote.md --candidate candidate.json
```

Model invocation is intentionally outside the trusted validator. Providers may
be local, Runtime Roost, or API-backed, but they must emit the same candidate
contract. This keeps credentials and provider-specific behavior out of the
public research build.
