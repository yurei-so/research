# Labnote 009 native Kokoro stress pilot

**Status:** Complete. Native synthesis passed naturalness, but the four-trial listener
pilot did not validate the intended focus mapping.

Labnote 008 proved that post-hoc token-local pitch editing can be audible while still
sounding layered and unnatural. This experiment removes DSP entirely and uses
Kokoro's documented Misaki stress representation before whole-utterance synthesis.

For two deterministically selected eligible contrastive-emphasis pairs and both established
voices, each condition keeps ordinary primary stress on the intended focus word and
demotes the competing focus word with Misaki's `[word](-1)` annotation. `(+2)` is not
used because installed-version verification showed it is a no-op on content words
that already carry primary stress.

The runner fails before GPU synthesis unless the phoneme manifest proves that:

- both focus words have primary stress in ordinary G2P;
- each annotated condition changes its competing word from primary to secondary;
- the intended word remains byte-identical at the phoneme level; and
- no non-focus token phonemes change.

Eligibility is evaluated before deterministic hashing. The authored corpus contains
three pairs where both competing focus words carry primary stress under the installed
Misaki G2P; pairs involving naturally secondary function words such as `I` or `She`
are excluded rather than coerced.

Audio is generated as a complete utterance by Kokoro. There is no segmentation,
splicing, pitch shifting, gain processing, time stretching, or crossfade stage.
`prepare_review.py` refuses to package a listener bundle unless every native-stress
trial passes the phoneme and bounded audio-integrity gates.

## Result

The approval-gated Agent Runtime/roostd run completed all four trials. Every condition
changed exactly one competing token from primary to secondary stress; all intended and
non-focus phonemes remained unchanged. Audio pairs were distinct and duration drift was
0.9–3.7 percent.

The operator reported that native whole-utterance synthesis sounded much better than
the rejected DSP pilots, with none of the prior layering complaint. This clears the
qualitative naturalness gate for the mechanism. The completed blinded preferences were:

- intended stress: 1;
- alternate stress: 2; and
- tie: 1.

This corpus is too small for general claims, and the direction does not support the
current focus-mapping rule. Native stress is therefore a viable artifact-free synthesis
primitive, not a validated context-to-prosody compiler. Do not expand it into the full
pipeline without a new hypothesis about how discourse focus should map to Kokoro's
phoneme stress representation.
