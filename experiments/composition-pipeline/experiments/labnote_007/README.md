# Labnote 007 matched deep-thinking composition campaign

This experiment compares `qwen3:8b` against itself on twelve bounded rewrite tasks. The
only treatment difference is Ollama's thinking control: one arm sets `think: false`, and
the other sets `think: true`. Prompt, task, draft, model, seed, temperature, final-output
instruction, token ceiling, and timeout are matched.

Raw prompts, final candidates, thinking traces, checkpoints, and treatment mappings stay
private. The runner publishes only aggregate operational telemetry. Identical outputs are
automatic ties. Blind review opens only if at least eight unique changed pairs survive,
and it never displays the thinking trace.

This is a reasoning-budget experiment, not a model comparison. A positive result requires
human preference strong enough to justify the measured latency and token overhead.

The completed campaign produced 24/24 valid generations and ten changed pairs for blind
review; two additional pairs were exact automatic ties. Thinking-enabled outputs won five
reviews, thinking-disabled outputs won four, and one was tied. With all pairs included,
the 5–4–3 disposition did not justify 8.3 times the latency and 16.6 times the generated
tokens. See the public Labnote 007 for the bounded negative result.
