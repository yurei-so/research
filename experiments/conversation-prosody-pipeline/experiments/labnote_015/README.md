# Labnote 015 emergent-reading annotation

This discovery pass reverses the failed direct-control framing. It blinds the eight
private Prosody 014 outputs, records what each performance actually expresses, and keeps
the source condition mapping in a separate owner-only reveal key.

Annotations include perceived focus, speech acts, affect, intensity, naturalness,
confidence, and optional observations. The loopback-only server validates an explicit
asset allowlist and appends each annotation durably. This pass creates a labeled private
corpus; it does not yet claim that acoustic fingerprints can predict those labels.

After all eight labels are locked, `analyze_annotations.py` verifies the bundle-to-key
binding, joins the hidden conditions, and writes an owner-only result. A requested focus
counts as named only when it appears as a complete comma-separated perceived-focus label;
the metric is descriptive and does not replace the annotator's richer notes.
