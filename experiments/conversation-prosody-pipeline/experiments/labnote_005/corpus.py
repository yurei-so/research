"""Deterministic authored replay corpus for Labnote 005a."""

from __future__ import annotations

import hashlib
import json
from typing import Any


TOPICS = (
    ("software", "repair the failing deployment", "the staging service"),
    ("travel", "plan a quieter train route", "the weekend trip"),
    ("cooking", "adjust the soup recipe", "dinner tonight"),
    ("gaming", "finish the legendary collection", "the next Guild Wars 2 step"),
    ("writing", "restructure the opening section", "the draft"),
    ("hardware", "diagnose the intermittent display", "the desktop"),
    ("scheduling", "move the appointment", "Friday afternoon"),
    ("gardening", "save the drooping basil", "the balcony planter"),
    ("budgeting", "compare the two purchase options", "the monthly budget"),
    ("learning", "practice the difficult chord change", "the guitar exercise"),
)

ARCHETYPES = ("direct", "reversal", "hesitation", "explanation", "completion")


def snapshot(text: str, time_ms: int, silence_ms: int, syntax_complete: bool,
             finality: float, speaking: bool = True) -> dict[str, Any]:
    return {
        "text": text,
        "time_ms": time_ms,
        "turn_state": {
            "silence_ms": silence_ms,
            "speech_active": speaking,
            "syntax_complete": syntax_complete,
            "prosodic_finality": finality,
        },
    }


def make_turn(index: int, topic_index: int, archetype: str, variant: int) -> dict[str, Any]:
    topic, action, obj = TOPICS[topic_index]
    alt_topic, alt_action, alt_obj = TOPICS[(topic_index + 3 + variant) % len(TOPICS)]
    prefix = ("Could you help me" if variant % 2 == 0 else "I want some help")
    if archetype == "direct":
        parts = [prefix, f"{prefix} figure out", f"{prefix} figure out how to {action}",
                 f"{prefix} figure out how to {action} for {obj}?"]
        safe = 2
        intent, final_topic = "request_guidance", topic
    elif archetype == "reversal":
        parts = [prefix, f"{prefix} figure out how to {action}",
                 f"{prefix} figure out how to {action}, actually wait",
                 f"actually, help me {alt_action} for {alt_obj} instead."]
        safe = 3
        intent, final_topic = "request_guidance", alt_topic
    elif archetype == "hesitation":
        parts = [prefix, f"{prefix}...", f"{prefix} figure out how to...",
                 f"{prefix} figure out how to {action} for {obj}."]
        safe = 3
        intent, final_topic = "request_guidance", topic
    elif archetype == "explanation":
        parts = [f"I'm working on {obj}", f"I'm working on {obj}, and I tried twice",
                 f"I'm working on {obj}, and I tried twice, but it still fails",
                 f"I'm working on {obj}; after two failures, can you help me {action}?"]
        safe = 3
        intent, final_topic = "request_guidance", topic
    else:
        parts = ["The word I'm looking for", "The word I'm looking for is the one that means",
                 f"the one that means helping someone {action}",
                 f"The word I'm looking for is related to {topic} and means helping someone {action}."]
        safe = 2
        intent, final_topic = "collaborative_completion", topic
    times = [900, 1900, 3100, 4300]
    snapshots = []
    for i, text in enumerate(parts):
        hesitation = archetype in ("hesitation", "completion") and i in (1, 2)
        snapshots.append(snapshot(
            text, times[i], 850 if hesitation else (700 if i == 3 else 120),
            i == 3, 0.92 if i == 3 else (0.15 if hesitation else 0.3), i != 3,
        ))
    return {
        "turn_id": f"t{index:03d}",
        "archetype": archetype,
        "variant": variant,
        "snapshots": snapshots,
        "true_turn_end_ms": 4300,
        "safe_semantic_commit_snapshot": safe,
        "gold_endpoint": {"intent": intent, "topic": final_topic},
        "late_reversal": archetype == "reversal",
        "completion_opportunity": archetype == "completion",
    }


def build_corpus() -> list[dict[str, Any]]:
    turns = []
    index = 1
    for archetype in ARCHETYPES:
        for topic_index in range(len(TOPICS)):
            for variant in range(4):
                turns.append(make_turn(index, topic_index, archetype, variant))
                index += 1
    assert len(turns) == 200
    return turns


def corpus_hash() -> str:
    payload = json.dumps(build_corpus(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
