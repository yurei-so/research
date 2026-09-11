# Labnote 012 reference-conditioned focus transfer

This bounded pilot asks whether whole-utterance reference conditioning can reproduce a
demonstrated contrastive focus without post-hoc DSP. Four private recordings from one
consenting speaker cover two unchanged sentences and both authored focus readings.
Two frozen seeds produce eight outputs.

The output voice is not treated as independently controlled. F5-TTS conditions speaker
identity and style together; this tests same-speaker focus reproduction and makes no
voice/prosody disentanglement claim.

Validate private references with `validate_references.py`, then run
`run_transfer.py` inside an isolated F5-TTS environment. Passing integrity does not
authorize listener review: naturalness and directional-focus gates remain mandatory.

The official F5-TTS code is MIT licensed; its pretrained weights are CC-BY-NC. This is
noncommercial research. The runner never downloads or publishes reference audio itself.
