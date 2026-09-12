# Labnote 013 Qwen instruction-conditioned focus pilot

**Status:** Complete negative result. All eight outputs passed mechanical integrity and
the owner-local naturalness floor, but the set failed directional-focus admission. No
blinded review was performed.

This bounded pilot tests whether Qwen3-TTS natural-language instructions can move
contrastive focus while preserving natural whole-utterance speech. It reuses the two
sentence pairs from Prosody 012, one frozen English preset voice, and two seeds per
condition for eight outputs.

There is no reference audio, voice cloning, DSP, or fine-tuning. The paired instructions
are symmetric: each names the intended focus and explicitly excludes the competing word.
Passing mechanical integrity does not authorize blinded review; all outputs must first
pass owner-local naturalness and directional-focus admission.

The Qwen3-TTS code and selected model are Apache-2.0 licensed. Generated audio and review
state remain private unless separately cleared for publication.
