# Amendment 001: duration integrity gate

Recorded before any generated output was listened to or judged.

The original runner treated generated/reference total-duration ratio `0.65–1.5`
as an integrity predicate. The interactive reference-capture workflow necessarily
included the time between starting the recorder and receiving the operator's
completion message. Valid references therefore contained long leading and trailing
silence while the generated file contained only the target utterance. All eight
outputs were created, had unique hashes, and were approximately two seconds long,
but the padded-reference ratio rejected every one.

The corrected mechanical gate requires exactly eight unique WAV hashes and a
generated duration from `0.8–8.0` seconds. Reference duration and the old ratio are
retained in the private report as diagnostics. This amendment does not inspect,
score, trim, transform, or select audio, and it does not change the mandatory
naturalness or directional-focus gates.
