# Migration ledger

This ledger distinguishes imported history from source-repository retirement.
Importing a project does not authorize deletion, archival, or remote changes to
its source repository.

| Project | Destination | Source branch | Source revision | Import | Verification | Source retirement |
| --- | --- | --- | --- | --- | --- | --- |
| `composition-review` | `apparatus/composition-review` | `dev` | `417edaf` | Imported with full history in `2b9c04a` | 8/8 tests pass | Not authorized |
| `conversation-prosody-pipeline` | `experiments/conversation-prosody-pipeline` | `experiment/labnote-004-listener-review` | `fcf8e2d` | Imported with full history in `58b94f6` | 39/39 tests pass; 11 notes indexed | Not authorized |
| `composition-pipeline` | `experiments/composition-pipeline` | `dev` | `197ca75` | Imported with full history in `ba21002` | 35/35 tests pass; 6 notes indexed | Not authorized |
| `zenith-vision` | `experiments/zenith-vision` | `dev` | `fc011d0` | Imported with full history in `80c7206` | 108/108 tests pass; 17 notes indexed | Not authorized |
| `prosody-demo` | `demos/prosody-demo` | `main` | `ff60e40` | Imported with full history in `cd6808c` | 7/7 Python and 1/1 JS tests pass | Not authorized |

## Initial apparatus slice

`composition-review` is the first import because it is clearly reusable human-
review apparatus, is small, has a clean working tree, and does not require a
classification decision. The original checkout remains untouched.

## Archive-readiness gate

A source repository is ready to archive only after this migration branch is
merged to `main`, remote `main` contains every recorded source revision, and a
clean checkout repeats the relevant verification. Archival must preserve the
source repository read-only; deletion is not part of this migration.
