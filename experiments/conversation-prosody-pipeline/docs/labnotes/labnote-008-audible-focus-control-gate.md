---
schema_version: 1
id: prosody-008
title: "audible focus-control gate"
date: 2026-08-23
status: complete
outcome: negative
question: "Can post-hoc focus control create audible, natural emphasis before spending human-review labor?"
tags: ["blinded-review","conversational-prosody","negative-result","prosody-control"]
lineage: ["prosody-004"]
publish: true
---
# Labnote 008 audible focus-control gate

**Status:** Complete negative result. Post-hoc focus editing remained perceptibly
artifacted and was rejected before listener judgments.

Labnote 004 showed that distinct audio bytes are not evidence of a meaningful
prosodic contrast. Its first listener slice was stopped after three blinded judgments:
delivery labels were never compiled, and focus was represented only as gain.

This bounded follow-up tests one mechanism before spending more human-review labor:
can a compiler place clearly audible emphasis on either of two authored focus spans
while holding sentence and voice fixed?

The v1 pilot passed its acoustic gate, but the operator heard an unnaturally high
pitch and a brief doubled voice at the edited boundary. No judgments were submitted.
The likely causes were a three-semitone shift with shifted formants and hard joins.

The frozen smooth-focus revision:

- deterministically selects two authored `contrastive-emphasis` pairs;
- evaluates both `af_heart` and `am_adam`;
- starts each comparison from the same neutral waveform;
- applies token-aligned +1.5-semitone, +3.5 dB emphasis with preserved formants,
  quality pitch processing, smooth transient handling, and 15 ms boundary overlap;

- admits a comparison only when both directions clear energy, token-local F0,
  waveform-separation, and duration-stability gates.

An initial v2 pass at +2.5 dB preserved pitch and duration but failed the frozen local
energy threshold. V3 changed only gain to +3.5 dB and qualified all four trials for
review.

The runner creates analysis artifacts only. `prepare_review.py` is a separate step
that refuses to produce a blinded listener bundle unless every frozen trial passed.

```bash
python experiments/labnote_008/run_focus_gate.py \
  --source-run artifacts/labnote-004/oracle-synthesis \
  --output-dir artifacts/labnote-008/focus-gate
```

## Result

The v3 four-question bundle passed every numerical acoustic intake gate. On the
pre-judgment listening check, however, the operator immediately recognized the same
unnatural voice effect that motivated the later native-synthesis experiments. Smooth
transient handling and preserved formants did not remove the perceptible post-hoc DSP
artifact. The review was stopped with zero judgments submitted.

This is a negative gate result: audibility and bounded waveform metrics were
insufficient proxies for natural, usable emphasis. Continuing the blinded preference
test would have measured tolerance for an obvious synthesis artifact rather than
focus recovery. Labnote 009 therefore removed token-local DSP entirely and tested
native whole-utterance lexical stress instead.
