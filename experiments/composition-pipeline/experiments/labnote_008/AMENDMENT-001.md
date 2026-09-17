# Amendment 001 — split binary review serialization

The completed generation campaign produced three arms and two preregistered pairwise
comparisons. Before any human review opened, intake validation found that Composition
Review's version 1 text bundle correctly permits only one binary arm mapping per bundle.
Serializing both controls into one bundle would either fail validation or collapse two
scientifically distinct controls under one label.

No generation prompt, case, seed, output, trial status, gate, or comparison changed. The
same sealed candidates are serialized into two version 3 text-review sessions instead:
`direct` versus `deferred_infill`, followed by `full_revision` versus
`deferred_infill`. Version 3 changes only the review envelope by naming both arms; review
presentation, deterministic counterbalancing, append-only judgments, and sealed reveal
remain unchanged. This amendment was recorded before any judgment was shown or committed.
