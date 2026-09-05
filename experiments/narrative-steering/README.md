# Narrative Steering Research

This experiment family measures how language models steer matched story states,
including changes to protagonist agency, affect, social support, causal fortune,
closure, escalation, and intimacy.

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

Run the tests with:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```
