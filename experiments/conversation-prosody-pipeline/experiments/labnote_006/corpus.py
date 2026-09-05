"""Deterministic multi-turn corpus for familiarity-gated speculation."""

from __future__ import annotations

import hashlib
import json

TOPICS = (
    ("software", "repair the deployment", "check logs", "isolate the failing service"),
    ("travel", "plan the train trip", "compare routes", "choose the quieter route"),
    ("cooking", "fix tonight's soup", "check seasoning", "adjust salt and acidity"),
    ("gaming", "plan the next collection step", "check requirements", "sequence the achievements"),
    ("writing", "revise the opening", "identify the thesis", "restructure the first section"),
    ("hardware", "diagnose the display", "check connections", "isolate the intermittent fault"),
    ("scheduling", "move the appointment", "compare availability", "propose a new time"),
    ("gardening", "help the basil recover", "check soil and light", "adjust watering"),
    ("budgeting", "compare the purchases", "list constraints", "rank the options"),
    ("learning", "practice the chord change", "slow the transition", "build a repetition drill"),
)
ARCHETYPES = ("direct", "implicit", "hesitation", "reversal", "completion")
MOVES = ("give_steps", "clarify", "offer_completion")
STRATEGIES = ("diagnose_then_act", "compare_then_choose", "explain_then_sequence")


def build_corpus(session_count: int = 40, turns_per_session: int = 25) -> list[dict]:
    sessions = []
    for session_index in range(session_count):
        stable = session_index % 4 != 3
        home_topic = session_index % len(TOPICS)
        style = ("Could you", "Can we", "I think we should", "Help me")[session_index % 4]
        turns = []
        for turn_index in range(turns_per_session):
            archetype = ARCHETYPES[(turn_index + session_index) % len(ARCHETYPES)]
            if stable:
                topic_index = (home_topic + turn_index // 10) % len(TOPICS)
            else:
                topic_index = (home_topic + turn_index * 3) % len(TOPICS)
            topic, goal, first_step, second_step = TOPICS[topic_index]
            alternate = TOPICS[(topic_index + 4) % len(TOPICS)]
            early = f"{style} help me with {topic}"
            final_topic, final_goal = topic, goal
            if archetype == "direct":
                final = f"{style} help me {goal}?"
                move = "give_steps"
            elif archetype == "implicit":
                early = f"I've been thinking about {topic} again"
                final = f"I've been thinking about {topic} again; what should I do next to {goal}?"
                move = "give_steps"
            elif archetype == "hesitation":
                early = f"{style} help me... with the {topic} thing..."
                final = f"{style} help me {goal}, starting with how to {first_step}?"
                move = "give_steps"
            elif archetype == "reversal":
                early = f"{style} help me {goal}"
                final_topic, final_goal = alternate[0], alternate[1]
                final = f"Actually, forget {topic}; {style.lower()} help me {final_goal} instead?"
                move = "give_steps"
            else:
                early = f"The phrase I'm looking for, about {topic}, is"
                final = f"The phrase I'm looking for describes how to {goal}; can you help me finish it?"
                move = "offer_completion"
            strategy = STRATEGIES[(topic_index + turn_index) % len(STRATEGIES)]
            turns.append({
                "turn_id": f"s{session_index:02d}-t{turn_index:02d}", "index": turn_index,
                "archetype": archetype, "early_text": early, "final_text": final,
                "snapshot_time_ms": 3000, "true_turn_end_ms": 4300,
                "gold_endpoint": {"intent": "collaborative_completion" if move == "offer_completion" else "request_guidance",
                                  "topic": final_topic},
                "gold_skeleton": {"response_move": move, "strategy": strategy},
                "topic": final_topic, "reversal": archetype == "reversal",
            })
        sessions.append({"session_id": f"session-{session_index:02d}", "stable": stable,
                         "style": style, "turns": turns})
    return sessions


def corpus_hash() -> str:
    return hashlib.sha256(json.dumps(build_corpus(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
