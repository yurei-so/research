# Narrative Steering Research

This experiment family measures how language models steer matched story states,
including changes to protagonist agency, affect, social support, causal fortune,
closure, escalation, and intimacy.

Executable software in this experiment family is AGPL-3.0-only. Labnotes,
datasets, frozen inputs, and generated artifacts are separate research content;
see [the directory license](LICENSE) and the
[repository licensing policy](../../LICENSE.md).

The first labnote deliberately uses a vector representation. Cone geometry,
attractor visualization, and claims about a model's latent policy are out of
scope until repeated measurements demonstrate a stable signal.

## Layout

- `docs/labnotes/` — canonical research record.
- `experiments/labnote_001/` — frozen corpus, protocol, and bounded scripts.
- `src/narrative_steering/` — validation, blinding, and aggregation logic.
- `tests/` — deterministic contract tests.

The pilot does not call a model directly. Generation is a separately approved
campaign that must produce the frozen input contract. Review preparation strips
model identity and writes owner-private bundle and reveal files.

The frozen local campaign uses digest-pinned `qwen3:8b`, `gemma3:12b`, and
`llama3.2:latest` models. `run_generation.py` checkpoints after every response
and refuses to continue if any installed model digest drifts.

`compile_fingerprint.py` produces state-bootstrap intervals and leave-one-state-
out stability diagnostics. Its optional scorer-calibration path evaluates a
complete blinded automated score set against locked human judgments and grants
assisted-expansion eligibility separately for each coordinate.

Run the tests with:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```
