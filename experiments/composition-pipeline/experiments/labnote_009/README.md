# Labnote 009 readiness-gated bounded-span repair

This experiment follows the negative forced-hole result in Labnote 008. It tests whether
two missing capabilities—an observable readiness condition derived from generated suffix
context and permission to rewrite a bounded provisional span—can make deferred
composition competitive.

The treatment draft marks one provisional span, declares what later evidence makes it
ready, continues generating, and emits `[[READY_1]]` only after that evidence appears.
The runtime then supplies text through that marker to a second call, which may replace
the entire marked span. The runtime removes protocol markers and performs the replacement
deterministically. This remains a text-level protocol with no tokenizer changes or model
training.

Eight new tasks avoid adapting to the revealed Labnote 008 corpus. The readiness-span arm
is reviewed separately against the failed hole-only mechanism and an unrestricted
two-pass revision control.
