# Migration ledger

This ledger distinguishes imported history from source-repository retirement.
Importing a project does not authorize deletion, archival, or remote changes to
its source repository.

| Project | Destination | Source branch | Source revision | Import | Verification | Source retirement |
| --- | --- | --- | --- | --- | --- | --- |
| `composition-review` | `apparatus/composition-review` | `dev` | `417edaf` | Imported with full history in `2b9c04a` | 8/8 tests pass | Not authorized |
| `conversation-prosody-pipeline` | `experiments/conversation-prosody-pipeline` | `experiment/labnote-004-listener-review` | `fcf8e2d` (includes one local unpushed commit) | Pending | Pending | Not authorized |
| `composition-pipeline` | `experiments/composition-pipeline` | `dev` | `197ca75` | Pending | Pending | Not authorized |
| `prosody-demo` | To classify: experiment or graduated reference | `main` | `ff60e40` | Deferred | Pending | Not authorized |

## First slice

`composition-review` is the first import because it is clearly reusable human-
review apparatus, is small, has a clean working tree, and does not require a
classification decision. The original checkout remains untouched.
