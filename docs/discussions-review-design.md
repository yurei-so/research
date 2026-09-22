# GitHub Discussions review design note

## Status

Future design only. This note does not authorize automation, create a GitHub
Discussion, or change the publication workflow.

## Question

Could GitHub Discussions provide a transparent, human-approval layer for new
labnotes without allowing a model or build job to publish research by itself?

## Proposed boundary

An automation may prepare a draft labnote, validator report, source revision,
and proposed metadata in a dedicated Discussion. It may not merge, publish, or
change canonical research records. A named human reviewer must record an
explicit decision against the immutable candidate revision.

The approval record should include:

- candidate and source hashes;
- apparatus, model, and prompt versions;
- deterministic validation output;
- human review scores, edits, and rationale;
- an explicit `approve`, `request changes`, or `reject` decision;
- the commit or pull request that incorporates an approved candidate.

Discussion reactions, silence, labels applied by an untrusted automation, and
model-authored comments are not approval. Editing a candidate after approval
invalidates that approval and requires a new review against the new hash.

## Possible workflow

1. Generate and validate a shadow candidate.
2. Open a Discussion containing the immutable review bundle.
3. Collect public feedback without treating it as authority.
4. Require an authorized human decision tied to the candidate hash.
5. If approved, open a pull request that references the Discussion and review
   decision; normal repository review and merge policy still apply.
6. Preserve rejected and revised candidates as experiment observations.

## Questions to resolve before implementation

- Which GitHub identities may approve, and how is that allowlist maintained?
- Should one reviewer suffice, or should public activation require two?
- How are private or embargoed source materials represented without disclosure?
- What retention and moderation policy applies to public feedback?
- How does automation verify an approval without granting itself publication
  authority?
- Should the durable approval record live in-repository as well as in GitHub?

Any implementation should begin as a separate Meta Research experiment and
remain shadow-only until spoofing, edit-after-approval, outage, and rollback
paths have been tested.
