# Labnote 010 native stress prominence gate

**Status:** Complete negative result. Native lexical stress did not create reliable
directional discourse prominence.

This experiment determines whether Misaki primary/secondary stress produces reliable
word-level acoustic prominence rather than merely clean lexical pronunciation. It uses
all three eligible Labnote 009 contrasts across both voices and whole-utterance Kokoro
generation from token lists, preserving model-generated token timestamps.

For each competing focus word, primary stress must beat secondary stress in at least
two of local RMS energy, duration, and median F0 by 3 percent, with no dimension below
0.90. A pair/voice trial passes only when both words pass. Campaign intake requires at
least 5/6 trials overall and at least 2/3 for each voice. No DSP is permitted, and no
human review is prepared from a failed campaign.

## Result

The approval-gated Agent Runtime/roostd run completed synthesis and analysis, then
exited with the intentional failed-gate status. Zero of six pair/voice trials passed;
only two of twelve individual focus words cleared the two-dimension rule. Some words
changed duration or energy, but effects were inconsistent, and median F0 remained
approximately flat. Neither voice cleared a trial.

This explains Labnote 009: Misaki primary/secondary stress can produce clean native
speech, but its lexical-stress annotation does not reliably implement discourse-level
contrastive focus. Do not spend more listener labor or tune thresholds around this
mechanism. A future prosody compiler requires a model or interface with explicit
utterance-level style/prosody conditioning.
