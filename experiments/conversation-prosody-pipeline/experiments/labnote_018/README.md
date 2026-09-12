# Labnote 018 conversation-conditioned two-speaker pilot

This bounded pilot renders one six-turn scene twice with Qwen3-TTS CustomVoice. The
isolated arm gives every turn the same generic conversational instruction. The
conversation-aware arm gives each turn an authored reaction and delivery direction
grounded in the surrounding scene. Text, speakers, seeds, generation settings, and
turn gaps remain identical between arms.

The runner writes private per-turn clips, two assembled conversations, and a mechanical
integrity report. It does not select candidates, edit generated speech, infer speaker
traits, or establish that context-aware direction is better. The two complete renders
must be reviewed blind for naturalness, conversational continuity, and turn timing.

The frozen run produced twelve mechanically valid turns. In blind whole-conversation
review, the isolated arm passed only turn timing while the conversation-aware arm passed
all four gates, including mutual reaction and complete-scene credibility. See the public
Labnote 018 for the bounded result and replication limits.
