# Labnote 001: Prompted and constrained editing baseline

## Question

Can an existing instruct model reliably produce useful, deterministically
applicable virtual-buffer operations without fine-tuning?

## Design

Six frozen, non-sensitive writing prompts are evaluated through three arms:

1. ordinary append-only generation;
2. prompted JSON edit operations without constrained decoding;
3. the same edit protocol with an Ollama JSON schema.

The runtime accepts only append, exact unique replacement, exact unique deletion,
and finalization. It records protocol validity, edit count, generated-token count,
visible output size, and latency. Final texts are retained only in Agent Runtime's
private experiment output for later blinded quality review.

## Interpretation boundary

Structural validity does not prove that edits improve writing. Fine-tuning is
not justified by a single bad run. It becomes a candidate only after prompt and
schema approaches repeatedly fail the frozen semantic-application threshold.

This experiment does not train a model, expose hidden reasoning, alter Chat
Runtime, or bypass roostd accelerator ownership.
