# Research governance

## What belongs here

- Hypotheses, protocols, labnotes, fixtures, analysis, and results.
- Bounded implementations whose primary purpose is answering a research
  question.
- Shared human-review, annotation, scoring, and evaluation apparatus.
- Negative and inconclusive results when they affect future decisions.

## What graduates

A project may move to a standalone repository when it has an independent
consumer contract, release lifecycle, operational deployment, or maintenance
identity beyond the experiment that produced it. The research repo keeps the
evidence trail and links to the exact graduated revision.

## Migration rules

1. Preserve original Git history and record the source repository, branch, and
   revision.
2. Never delete or archive a source repository in the same step as importing it.
3. Do not copy virtual environments, generated outputs, private review state,
   secrets, model caches, or machine-local inputs.
4. Keep frozen protocols and completed results immutable except for explicit
   errata.
5. Run the source project's tests from its imported location before marking a
   migration verified.
6. Treat repository retirement, redirects, and remote changes as separate,
   reviewable operations.

