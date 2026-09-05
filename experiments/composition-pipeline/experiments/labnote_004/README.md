# Labnote 004

This larger follow-up separates two questions that Labnote 003 could not answer
efficiently: whether optional editor access helps overall, and whether it helps
when it actually changes the matched output.

The runner executes 120 matched pairs. Each optional-editor result is compared
with its own pre-editor direct rewrite, preventing repeated generation from
confounding review inclusion. Normalized-identical final outputs are durably
counted as automatic ties and omitted from the human review bundle.
Every genuinely different pair enters the blinded bundle regardless of edit
size, protocol validity, similarity, or expected quality. The public result
reports both counts so the conditional review cannot hide the intervention
rate. Private prompts, text, operations, telemetry, and reveal mappings remain
in the owner-only state directory.
