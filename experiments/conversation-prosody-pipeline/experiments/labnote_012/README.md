# Labnote 012 reference-conditioned focus transfer

**Status:** Complete negative result. Eight mechanically valid outputs failed the
owner-local naturalness admission gate, so directional scoring and blinded review were
not performed.

This bounded pilot asks whether whole-utterance reference conditioning can reproduce a
demonstrated contrastive focus without post-hoc DSP. Four private recordings from one
consenting speaker cover two unchanged sentences and both authored focus readings.
Two frozen seeds produce eight outputs.

The output voice is not treated as independently controlled. F5-TTS conditions speaker
identity and style together; this tests same-speaker focus reproduction and makes no
voice/prosody disentanglement claim.

Capture the four private references with `record_references.sh`. It records mono,
48 kHz, 16-bit WAV files into an owner-only directory outside the repository and
refuses to overwrite an existing take. Set `PROSODY_012_REFERENCE_DIR` to choose a
different private location.

Validate private references with `validate_references.py`, then run
`run_transfer.py` inside an isolated F5-TTS environment. Passing integrity does not
authorize listener review: naturalness and directional-focus gates remain mandatory.
`amendment-001.md` records a pre-listening correction to the mechanical duration
gate after interactive capture padding made total reference duration unsuitable.

The official F5-TTS code is MIT licensed; its pretrained weights are CC-BY-NC. This is
noncommercial research. The runner never downloads or publishes reference audio itself.
