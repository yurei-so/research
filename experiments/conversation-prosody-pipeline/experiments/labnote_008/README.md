# Labnote 008 audible focus-control gate

**Status:** v1 was audible but failed naturalness; v2 smooth-focus gate pending.

Labnote 004 showed that distinct audio bytes are not evidence of a meaningful
prosodic contrast. Its first listener slice was stopped after three blinded judgments:
delivery labels were never compiled, and focus was represented only as gain.

This bounded follow-up tests one mechanism before spending more human-review labor:
can a compiler place clearly audible emphasis on either of two authored focus spans
while holding sentence and voice fixed?

The v1 pilot passed its acoustic gate, but the operator heard an unnaturally high
pitch and a brief doubled voice at the edited boundary. No judgments were submitted.
The likely causes were a three-semitone shift with shifted formants and hard joins.

The frozen v2 pilot:

- deterministically selects two authored `contrastive-emphasis` pairs;
- evaluates both `af_heart` and `am_adam`;
- starts each comparison from the same neutral waveform;
- applies token-aligned +1.5-semitone, +3.5 dB emphasis with preserved formants,
  quality pitch processing, smooth transient handling, and 15 ms boundary overlap;

An initial v2 pass at +2.5 dB preserved pitch and duration but failed the frozen local
energy threshold. v3 changes only gain to +3.5 dB; another failure ends this DSP route.
- admits a comparison only when both directions clear energy, token-local F0,
  waveform-separation, and duration-stability gates.

The runner creates analysis artifacts only. `prepare_review.py` is a separate step
that refuses to produce a blinded listener bundle unless every frozen trial passed.

```bash
python experiments/labnote_008/run_focus_gate.py \
  --source-run artifacts/labnote-004/oracle-synthesis \
  --output-dir artifacts/labnote-008/focus-gate
```

Once the gate passes, prepare the four-question audio pilot with explicit private
state and calibration paths. Human review remains blinded and separately launched.
