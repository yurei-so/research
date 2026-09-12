# Labnote 016 acoustic fingerprint pilot

This pilot measures the eight privately labeled Prosody 015 clips without generating
new audio. `align_words.py` obtains word timestamps; `extract_fingerprints.py` independently
computes deterministic pitch, energy, timing, pause, contour, and word-prominence features.

Audio, timestamps, labels, item-level fingerprints, and reveal mappings remain private.
Only aggregate results belong in the public labnote. With eight clips, this can test
whether the proposed representation is visibly aligned with the annotations, not train
or validate a classifier.
