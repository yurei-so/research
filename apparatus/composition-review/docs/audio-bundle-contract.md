# Blinded audio bundle contract

Audio mode uses `composition-pipeline.blinded-review` version 2. The public
bundle contains safe review context, an asset allowlist, and opaque A/B asset
IDs. The separate owner-only reveal key contains the two arm identifiers and
pair mappings. Arm identifiers never enter the pre-completion session API.

```json
{
  "format": "composition-pipeline.blinded-review",
  "version": 2,
  "campaign_digest": "...",
  "mode": "audio",
  "calibration_asset": "calibration-or-null",
  "assets": [
    {
      "asset_id": "clip-a",
      "file_name": "clip-a.wav",
      "sha256": "64 lowercase hexadecimal characters",
      "media_type": "audio/wav"
    }
  ],
  "pairs": [
    {
      "pair_id": "opaque-pair-id",
      "case_id": "safe-case-id",
      "prompt_style": "listener",
      "repetition": 0,
      "task": "Which delivery better matches the stated reading?",
      "draft": "Safe context and fixed target text.",
      "candidate_a_asset": "clip-a",
      "candidate_b_asset": "clip-b",
      "criteria": ["naturalness"]
    }
  ]
}
```

The matching reveal key is version 2 and adds `baseline_arm` and
`treatment_arm`. It otherwise preserves the existing per-pair A/B mapping and
bundle-digest binding.

Security invariants:

- The asset root is an explicit absolute server configuration value.
- Manifest file names are single safe path components; paths and URLs never
  come from model output.
- Every declared asset must be a regular non-symlink file whose SHA-256 matches
  before the review server starts.
- Only declared opaque asset IDs are served, only to an enrolled browser, with
  private no-store responses.
- Candidate arms remain hidden until every append-only judgment is committed.
- The readiness gate is browser-local convenience state, not an authorization
  boundary or a substitute for a formal hearing test.
