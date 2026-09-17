# Labnote 008 forced deferred-hole composition pilot

This bounded campaign compares three matched composition paths on eight authored rewrite
tasks: a one-pass direct rewrite, that same rewrite followed by unrestricted revision, and
a draft forced to carry one typed `[[DEFER_1:TYPE]]` hole into later right-hand context
before a constrained infill call resolves it.

The experiment requires no tokenizer changes or model training. Placeholders are ordinary
text governed by a runtime protocol. The runner validates exactly one declared hole,
requires meaningful right-hand context after it, accepts only a bounded replacement from
the second call, and performs literal replacement itself. Nested or unresolved holes fail
the trial.

The unrestricted two-pass arm controls for the extra model call. Human review compares
the deferred result independently against both direct and full-revision candidates. This
pilot tests whether the mechanism helps composition; it does not claim access to internal
uncertainty or validate an adaptive uncertainty trigger.
