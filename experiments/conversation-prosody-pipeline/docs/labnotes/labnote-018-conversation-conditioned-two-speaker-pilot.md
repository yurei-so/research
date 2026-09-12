---
schema_version: 1
id: prosody-018
title: "conversation-conditioned two-speaker pilot"
date: 2026-09-12
status: complete
outcome: positive
question: "Can conversation-aware turn direction produce a convincing two-speaker exchange where isolated line direction does not?"
tags: ["conversational-prosody","multi-speaker","synthetic-audio","turn-taking"]
lineage: ["prosody-017"]
relations: [{"target":"prosody-017","type":"reuses-apparatus","rationale":"Reuses its validated Qwen3-TTS CustomVoice synthesis path while moving evaluation from isolated utterances to a complete two-speaker scene."}]
publish: true
---
# Labnote 018: conversation-conditioned two-speaker pilot

## Question

Can conversation-aware turn direction produce a convincing two-speaker exchange where
isolated line direction does not?

## Frozen pilot

- One authored, low-stakes six-turn exchange between two alternating housemates.
- Two distinct Qwen3-TTS 1.7B CustomVoice preset speakers.
- An isolated arm giving every line the same generic conversational instruction.
- A conversation-aware arm giving each line an authored reaction and delivery direction
  grounded in the shared scene.
- Identical text, speakers, per-turn seeds, generation settings, and silence gaps across
  both arms.
- No candidate selection or speech editing; only deterministic silence was inserted when
  assembling the generated turns.
- Blind review of the two complete conversations before arm identity was revealed.

The listener judged four whole-scene gates: natural individual voices, apparent reaction
between speakers, conversational turn timing, and whether the complete exchange was
convincing.

## Result

All twelve turn files were unique and passed the frozen mechanical duration checks. The
isolated and conversation-aware assemblies were 12.61 and 13.25 seconds respectively.

Before reveal, the isolated render passed only the turn-timing gate. Its voices were not
judged natural, the speakers did not sound like they were reacting to each other, and the
complete exchange was not convincing. The conversation-aware render passed all four
gates: its voices sounded natural, its turns sounded mutually responsive, its timing felt
conversational, and the complete scene was judged convincing.

This is positive evidence that broad, scene-grounded performance direction can produce a
convincing short two-speaker render with the current local apparatus. It is not evidence
that dialogue context reliably causes the improvement: the pilot contains one scene, one
sample per arm, and one listener, and its authored directions differ turn by turn. A
replication should freeze multiple scenes and seeds, preserve blind whole-conversation
review, and include an ablation separating shared scene context from per-turn performance
direction.

