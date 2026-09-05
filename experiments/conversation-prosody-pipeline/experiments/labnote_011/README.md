# Labnote 011 reproducible Amy-LM rerun

This reruns Labnote 003 without its opaque audio. A revision-pinned Dataset Viewer
snapshot supplies 20 text rows but is not redistributed because its license is absent.
Kokoro renders each `rewritten_text` as a whole utterance with `af_heart`, speed 1.0,
24 kHz PCM, and no post-processing. The runner fingerprints every input and output.

```bash
PYTHONPATH=src .venv-kokoro/bin/python experiments/labnote_011/run_rerun.py \
  --source-snapshot /path/to/rows.json \
  --run-dir artifacts/labnote-011/reproducible-rerun
```

The first invocation intentionally stops after synthesis. Independent ASR must produce
`{"<row index>": "transcript"}`. Rerun with `--transcripts-json`; add `--generate`
only after the fidelity and treatment-separation gates pass.
