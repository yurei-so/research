"""Authored same-text/different-context benchmark for labnote 004."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DELIVERIES = (
    "neutral",
    "corrective",
    "uncertain",
    "confident",
    "genuine-question",
    "rhetorical-question",
    "parenthetical",
    "interrupted",
    "sarcastic",
    "sincere",
    "excited",
    "serious",
)
BOUNDARIES = ("none", "continuation", "final")
PACES = ("slow", "normal", "fast")


@dataclass(frozen=True)
class Reading:
    context: str
    focus_span: str | None
    focus_strength: int
    boundary: str
    delivery: str
    pace: str = "normal"


@dataclass(frozen=True)
class Contrast:
    phenomenon: str
    target: str
    readings: tuple[Reading, Reading]


def r(
    context: str,
    focus: str | None,
    strength: int,
    boundary: str,
    delivery: str,
    pace: str = "normal",
) -> Reading:
    return Reading(context, focus, strength, boundary, delivery, pace)


CONTRASTS: tuple[Contrast, ...] = (
    # Contrastive emphasis: context determines which unchanged constituent is focal.
    Contrast("contrastive-emphasis", "I sent the revised report yesterday.", (
        r("Morgan says Casey sent the revised report yesterday. Correct Morgan.", "I", 2, "final", "corrective"),
        r("Morgan says you sent the original report yesterday. Correct Morgan.", "revised", 2, "final", "corrective"),
    )),
    Contrast("contrastive-emphasis", "She ordered the blue curtains online.", (
        r("Someone says he ordered the blue curtains online. Correct them.", "She", 2, "final", "corrective"),
        r("Someone says she ordered the green curtains online. Correct them.", "blue", 2, "final", "corrective"),
    )),
    Contrast("contrastive-emphasis", "We meet at the library on Friday.", (
        r("Your friend thinks you meet at the cafe on Friday. Correct the location.", "library", 2, "final", "corrective"),
        r("Your friend thinks you meet at the library on Thursday. Correct the day.", "Friday", 2, "final", "corrective"),
    )),
    Contrast("contrastive-emphasis", "Jordan borrowed my bicycle again.", (
        r("Someone says Taylor borrowed your bicycle again. Correct the person.", "Jordan", 2, "final", "corrective"),
        r("Someone says Jordan borrowed your scooter again. Correct the object.", "bicycle", 2, "final", "corrective"),
    )),
    Contrast("contrastive-emphasis", "The backup finished before midnight.", (
        r("A teammate thinks the upload finished before midnight. Correct the process.", "backup", 2, "final", "corrective"),
        r("A teammate thinks the backup finished after midnight. Correct the timing.", "before", 2, "final", "corrective"),
    )),
    Contrast("contrastive-emphasis", "I only promised to review the draft.", (
        r("Someone says you promised to approve the draft. Narrow what you promised.", "review", 2, "final", "corrective"),
        r("Someone says Alex promised to review the draft. Correct who promised.", "I", 2, "final", "corrective"),
    )),

    # Correction versus ordinary confirmation.
    Contrast("correction", "The appointment is at three.", (
        r("They just said the appointment is at four. Correct them.", "three", 2, "final", "corrective"),
        r("They ask you to confirm that the appointment is at three. Confirm it plainly.", None, 0, "final", "neutral"),
    )),
    Contrast("correction", "Her name is Mara.", (
        r("Someone repeatedly calls her Maria. Correct the name.", "Mara", 2, "final", "corrective"),
        r("Someone asks what her name is. Answer without correcting anything.", None, 0, "final", "neutral"),
    )),
    Contrast("correction", "The train leaves from platform six.", (
        r("A traveler says it leaves from platform two. Correct the platform.", "six", 2, "final", "corrective"),
        r("A traveler asks which platform the train uses. Answer neutrally.", None, 0, "final", "neutral"),
    )),
    Contrast("correction", "We need the smaller adapter.", (
        r("A coworker reaches for the larger adapter. Correct their choice.", "smaller", 2, "final", "corrective"),
        r("A coworker asks which adapter the instructions specify. Answer neutrally.", None, 0, "final", "neutral"),
    )),
    Contrast("correction", "The meeting starts after lunch.", (
        r("Someone says the meeting starts before lunch. Correct them.", "after", 2, "final", "corrective"),
        r("Someone asks when the meeting starts. Answer plainly.", None, 0, "final", "neutral"),
    )),
    Contrast("correction", "I asked for decaf.", (
        r("The barista hands you regular coffee. Correct the order.", "decaf", 2, "final", "corrective"),
        r("A friend asks what you ordered. Answer plainly.", None, 0, "final", "neutral"),
    )),

    # Epistemic stance without changing words.
    Contrast("certainty", "That should be enough.", (
        r("You checked the measurements twice and know the amount is sufficient. Reassure them.", "enough", 1, "final", "confident"),
        r("You estimated quickly and are not sure the amount is sufficient. Offer the estimate cautiously.", "should", 1, "final", "uncertain", "slow"),
    )),
    Contrast("certainty", "I think the door is locked.", (
        r("You personally tested the lock. State your conclusion with confidence.", "locked", 1, "final", "confident"),
        r("You only vaguely remember locking it. Express real uncertainty.", "think", 1, "final", "uncertain", "slow"),
    )),
    Contrast("certainty", "It probably arrived this morning.", (
        r("The tracking page confirms a morning delivery. Speak with practical confidence.", "arrived", 1, "final", "confident"),
        r("You have not checked tracking and are guessing. Speak tentatively.", "probably", 1, "final", "uncertain", "slow"),
    )),
    Contrast("certainty", "This looks like the right cable.", (
        r("You verified the part number. Confirm the cable confidently.", "right", 1, "final", "confident"),
        r("The connectors look similar and you have not verified them. Hedge audibly.", "looks", 1, "final", "uncertain", "slow"),
    )),
    Contrast("certainty", "We can finish by Tuesday.", (
        r("All remaining work is scheduled and comfortably fits. Commit confidently.", "Tuesday", 1, "final", "confident"),
        r("Two dependencies are unresolved. Make the estimate cautiously.", "can", 1, "final", "uncertain", "slow"),
    )),
    Contrast("certainty", "The storm might miss us.", (
        r("The updated forecast clearly shows the storm turning away. Offer grounded reassurance.", "miss", 1, "final", "confident"),
        r("The forecast cone still covers your area. Emphasize uncertainty.", "might", 2, "final", "uncertain", "slow"),
    )),

    # Genuine information seeking versus a rhetorical challenge.
    Contrast("question-intent", "Do you really expect that to work?", (
        r("You are unfamiliar with the method and sincerely want the engineer to explain it.", "work", 1, "final", "genuine-question"),
        r("The same method has failed five times and you are challenging the proposal.", "really", 2, "final", "rhetorical-question"),
    )),
    Contrast("question-intent", "Is that your final answer?", (
        r("You need to record whether the contestant wants to lock in the answer.", "final", 1, "final", "genuine-question"),
        r("They keep changing their story and you are expressing disbelief.", "final", 2, "final", "rhetorical-question"),
    )),
    Contrast("question-intent", "Could this be any slower?", (
        r("You are benchmarking a system and literally asking whether a slower mode exists.", "slower", 1, "final", "genuine-question"),
        r("The loading screen has taken ten minutes and you are complaining sarcastically.", "slower", 2, "final", "rhetorical-question"),
    )),
    Contrast("question-intent", "Who would leave that there?", (
        r("You need to identify who placed an important package there.", "Who", 1, "final", "genuine-question"),
        r("A cart blocks the doorway and you are expressing exasperation, not seeking a name.", "there", 1, "final", "rhetorical-question"),
    )),
    Contrast("question-intent", "Are we calling that a plan?", (
        r("You are clarifying whether the sketch is the official plan.", "plan", 1, "final", "genuine-question"),
        r("The proposal has no dates or owners and you are criticizing it.", "plan", 2, "final", "rhetorical-question"),
    )),
    Contrast("question-intent", "Did you mean to send this?", (
        r("The attachment seems unusual and you sincerely want confirmation.", "send", 1, "final", "genuine-question"),
        r("The document is obviously unfinished and you are signaling disbelief.", "this", 2, "final", "rhetorical-question"),
    )),

    # Boundary intent: identical fragments can signal continuation or completion.
    Contrast("boundary", "We packed the charger, the cables, and the batteries.", (
        r("That is the complete packing list. Finish decisively.", None, 0, "final", "neutral"),
        r("You are about to add two more items after this phrase. Keep the list audibly open.", None, 0, "continuation", "neutral"),
    )),
    Contrast("boundary", "First we test the input, then the parser.", (
        r("Those are the only two test stages. Close the explanation.", None, 0, "final", "neutral"),
        r("You will next describe validation and publication stages. Signal continuation.", None, 0, "continuation", "neutral"),
    )),
    Contrast("boundary", "There were messages from Sam, Priya, and Lee.", (
        r("Those are all the messages. End the list.", None, 0, "final", "neutral"),
        r("You have not yet mentioned two other senders. Keep the list open.", None, 0, "continuation", "neutral"),
    )),
    Contrast("boundary", "The choices are red, silver, and black.", (
        r("Black is the final available color. Sound complete.", None, 0, "final", "neutral"),
        r("You are pausing before adding white and blue. Sound incomplete.", None, 0, "continuation", "neutral"),
    )),
    Contrast("boundary", "I checked the logs, the metrics, and the traces.", (
        r("That completes your diagnostic review. Finish the statement.", None, 0, "final", "neutral"),
        r("You will next mention packet captures and database records. Hold the floor.", None, 0, "continuation", "neutral"),
    )),
    Contrast("boundary", "We could walk, take the bus, or call a taxi.", (
        r("Those are the complete transportation options. Finish neutrally.", None, 0, "final", "neutral"),
        r("You are about to suggest renting bicycles too. Keep the list open.", None, 0, "continuation", "neutral"),
    )),

    # Parenthetical versus main-clause prominence.
    Contrast("parenthetical", "The deployment, as you probably noticed, finished early.", (
        r("The aside merely acknowledges what the listener saw; foreground the early finish.", "finished early", 1, "final", "parenthetical"),
        r("You are pointedly reminding the listener that they noticed it. Foreground the aside.", "you probably noticed", 2, "final", "corrective"),
    )),
    Contrast("parenthetical", "My brother, the one from Denver, is visiting.", (
        r("The Denver phrase only identifies which brother. Keep it in the background.", "visiting", 1, "final", "parenthetical"),
        r("Someone assumed you meant your brother from Austin. Contrast the Denver identification.", "Denver", 2, "final", "corrective"),
    )),
    Contrast("parenthetical", "The blue folder, not the green one, contains the contract.", (
        r("The color correction is crucial because they reached for green.", "not the green one", 2, "final", "corrective"),
        r("They already have the blue folder; simply explain what it contains.", "contract", 1, "final", "parenthetical"),
    )),
    Contrast("parenthetical", "The server, despite the warning, stayed online.", (
        r("The warning is background context; emphasize that service continued.", "stayed online", 1, "final", "parenthetical"),
        r("Someone claimed there was no warning. Emphasize that a warning existed.", "despite the warning", 2, "final", "corrective"),
    )),
    Contrast("parenthetical", "Your keys, if I remember correctly, are upstairs.", (
        r("You are uncertain about your memory. Let the aside carry the uncertainty.", "if I remember correctly", 1, "final", "uncertain", "slow"),
        r("You just saw the keys upstairs. Foreground the location confidently.", "upstairs", 1, "final", "confident"),
    )),
    Contrast("parenthetical", "The patch, which arrived this morning, fixes the crash.", (
        r("The arrival time is incidental; foreground the fix.", "fixes the crash", 1, "final", "parenthetical"),
        r("Someone thinks the patch arrived yesterday. Correct the timing.", "this morning", 2, "final", "corrective"),
    )),

    # Interruption/self-repair versus smooth final delivery.
    Contrast("interruption", "I was going to call her tomorrow.", (
        r("You are interrupted immediately after saying 'call her'; the thought is cut off.", "call her", 1, "continuation", "interrupted"),
        r("You are calmly stating the complete plan. Finish normally.", None, 0, "final", "neutral"),
    )),
    Contrast("interruption", "The second option is probably safer.", (
        r("You stop after 'probably' because someone talks over you. Sound cut off.", "probably", 1, "continuation", "interrupted"),
        r("You deliver the complete recommendation without interruption.", "safer", 1, "final", "confident"),
    )),
    Contrast("interruption", "We should move the meeting to Thursday.", (
        r("You are interrupted after 'move the meeting' before naming the day.", "move the meeting", 1, "continuation", "interrupted"),
        r("You state the rescheduling decision completely.", "Thursday", 1, "final", "confident"),
    )),
    Contrast("interruption", "I thought the package was downstairs.", (
        r("Halfway through, you see the package and abandon the thought. Sound self-interrupted.", "thought", 1, "continuation", "interrupted"),
        r("You finish explaining your earlier belief.", "downstairs", 1, "final", "neutral"),
    )),
    Contrast("interruption", "The password should still be in the vault.", (
        r("An alarm interrupts you just after 'still be'. Leave the thought hanging.", "still be", 1, "continuation", "interrupted"),
        r("You complete the location advice calmly.", "vault", 1, "final", "confident"),
    )),
    Contrast("interruption", "Maybe we can solve it another way.", (
        r("Someone cuts in after 'solve it'. Yield the floor mid-thought.", "solve it", 1, "continuation", "interrupted"),
        r("You finish offering the alternative thoughtfully.", "another way", 1, "final", "uncertain", "slow"),
    )),

    # Sarcasm versus sincerity.
    Contrast("sarcasm", "That was incredibly helpful.", (
        r("Their clear explanation solved the problem. Thank them sincerely.", "helpful", 1, "final", "sincere"),
        r("Their advice deleted the working configuration. Respond sarcastically.", "incredibly", 2, "final", "sarcastic"),
    )),
    Contrast("sarcasm", "What a brilliant idea.", (
        r("The idea elegantly solves a longstanding problem. Praise it sincerely.", "brilliant", 1, "final", "sincere"),
        r("The idea repeats the exact mistake that caused yesterday's outage. Mock it dryly.", "brilliant", 2, "final", "sarcastic"),
    )),
    Contrast("sarcasm", "This is exactly what I needed.", (
        r("The delivered part perfectly completes your repair. Express sincere relief.", "exactly", 1, "final", "sincere"),
        r("They delivered an unrelated broken part. Express sarcasm.", "exactly", 2, "final", "sarcastic"),
    )),
    Contrast("sarcasm", "You handled that beautifully.", (
        r("They de-escalated a tense situation with unusual care. Praise them sincerely.", "beautifully", 1, "final", "sincere"),
        r("They made the argument dramatically worse. Criticize them sarcastically.", "beautifully", 2, "final", "sarcastic"),
    )),
    Contrast("sarcasm", "Well, that went perfectly.", (
        r("A difficult procedure genuinely completed without any errors. Celebrate sincerely.", "perfectly", 1, "final", "sincere"),
        r("Every stage failed in a different way. Deliver the line with dry sarcasm.", "perfectly", 2, "final", "sarcastic"),
    )),
    Contrast("sarcasm", "I love waiting in traffic.", (
        r("You genuinely enjoy quiet time in the car and mean the statement literally.", "love", 1, "final", "sincere"),
        r("You are already late and traffic has not moved for twenty minutes. Be sarcastic.", "love", 2, "final", "sarcastic"),
    )),

    # Affect transition reflected in the same target line.
    Contrast("affect", "You actually made it.", (
        r("A friend arrives at the surprise party after months away. Greet them excitedly.", "made it", 2, "final", "excited", "fast"),
        r("A climber reaches shelter after a dangerous night. Acknowledge it with sober relief.", "made it", 1, "final", "serious", "slow"),
    )),
    Contrast("affect", "Everything is ready now.", (
        r("The stage is set and the audience is arriving. Announce it excitedly.", "ready", 1, "final", "excited", "fast"),
        r("Emergency preparations are complete as the storm approaches. State it seriously.", "now", 1, "final", "serious", "slow"),
    )),
    Contrast("affect", "We found the missing file.", (
        r("The file contains the photos everyone feared were lost. Celebrate.", "found", 2, "final", "excited", "fast"),
        r("The file is evidence in a serious incident review. Report the discovery soberly.", "missing file", 1, "final", "serious", "slow"),
    )),
    Contrast("affect", "The results are finally here.", (
        r("The team has awaited good competition results all day. Announce them excitedly.", "finally", 2, "final", "excited", "fast"),
        r("The medical test results require a careful private discussion. Introduce them seriously.", "results", 1, "final", "serious", "slow"),
    )),
    Contrast("affect", "They said yes.", (
        r("A beloved friend accepted a joyful invitation. Share the news excitedly.", "yes", 2, "final", "excited", "fast"),
        r("Officials approved a difficult evacuation decision. Report it gravely.", "yes", 1, "final", "serious", "slow"),
    )),
    Contrast("affect", "It starts tonight.", (
        r("A long-awaited festival begins tonight. Say it with anticipation.", "tonight", 2, "final", "excited", "fast"),
        r("A dangerous overnight operation begins tonight. State it with gravity.", "tonight", 1, "final", "serious", "slow"),
    )),

    # Information structure: discourse-given versus newly contrasted material.
    Contrast("information-structure", "Mina repaired the old radio.", (
        r("Everyone knows Mina repaired something; clarify that it was the old radio.", "old radio", 2, "final", "neutral"),
        r("Everyone knows the old radio was repaired; clarify that Mina did it.", "Mina", 2, "final", "neutral"),
    )),
    Contrast("information-structure", "The package arrived on Tuesday.", (
        r("Everyone knows the package arrived; provide the day.", "Tuesday", 2, "final", "neutral"),
        r("Everyone knows something arrived Tuesday; identify the package.", "package", 2, "final", "neutral"),
    )),
    Contrast("information-structure", "Our neighbor adopted the kitten.", (
        r("The kitten's adoption is known; identify who adopted it.", "neighbor", 2, "final", "neutral"),
        r("Your neighbor adopted one of two animals; identify the kitten.", "kitten", 2, "final", "neutral"),
    )),
    Contrast("information-structure", "The sensor failed during startup.", (
        r("The startup failure is known; identify the sensor as what failed.", "sensor", 2, "final", "neutral"),
        r("The sensor failure is known; identify startup as when it happened.", "startup", 2, "final", "neutral"),
    )),
    Contrast("information-structure", "Ravi chose the window seat.", (
        r("The window seat was chosen; identify Ravi as the person who chose it.", "Ravi", 2, "final", "neutral"),
        r("Ravi chose a seat; identify which seat he chose.", "window", 2, "final", "neutral"),
    )),
    Contrast("information-structure", "The update fixed the audio bug.", (
        r("The update fixed one issue; identify the audio bug as the issue.", "audio bug", 2, "final", "neutral"),
        r("The audio bug was fixed; identify the update as what fixed it.", "update", 2, "final", "neutral"),
    )),

    # Pace intent under controlled wording.
    Contrast("pace", "We need to leave right now.", (
        r("Smoke is entering the hallway and immediate evacuation is necessary. Speak urgently.", "right now", 2, "final", "serious", "fast"),
        r("You are gently ending a difficult visit without immediate danger. Speak deliberately.", "leave", 1, "final", "serious", "slow"),
    )),
    Contrast("pace", "Let me explain what happened.", (
        r("You have only ten seconds before the call disconnects. Begin quickly.", "explain", 1, "continuation", "serious", "fast"),
        r("The listener is upset and needs a careful account. Begin slowly.", "explain", 1, "continuation", "serious", "slow"),
    )),
    Contrast("pace", "There is one more thing.", (
        r("You remember an urgent detail as they are walking away. Get their attention quickly.", "one more thing", 2, "continuation", "serious", "fast"),
        r("You are about to disclose something difficult. Introduce it deliberately.", "one more thing", 1, "continuation", "serious", "slow"),
    )),
    Contrast("pace", "I can show you how it works.", (
        r("The demonstration window closes in moments. Offer quickly.", "show", 1, "final", "confident", "fast"),
        r("The learner is overwhelmed and needs patience. Offer slowly and reassuringly.", "how it works", 1, "final", "sincere", "slow"),
    )),
    Contrast("pace", "We should check every connection.", (
        r("The system must restart in one minute. Give the instruction urgently.", "every", 2, "final", "serious", "fast"),
        r("You are teaching a careful diagnostic process with no time pressure. Speak deliberately.", "every connection", 1, "final", "confident", "slow"),
    )),
    Contrast("pace", "Tell me exactly what you saw.", (
        r("An event is unfolding and responders need the information immediately. Ask urgently.", "exactly", 2, "final", "serious", "fast"),
        r("The witness is shaken and needs time. Ask gently and slowly.", "what you saw", 1, "final", "sincere", "slow"),
    )),
)


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for contrast_index, contrast in enumerate(CONTRASTS, start=1):
        pair_id = f"p{contrast_index:03d}"
        for reading_index, reading in enumerate(contrast.readings, start=1):
            case_id = f"{pair_id}-r{reading_index}"
            cases.append({
                "case_id": case_id,
                "pair_id": pair_id,
                "reading": reading_index,
                "phenomenon": contrast.phenomenon,
                "context": reading.context,
                "target": contrast.target,
                "gold_ir": {
                    "focus_span": reading.focus_span,
                    "focus_strength": reading.focus_strength,
                    "boundary": reading.boundary,
                    "delivery": reading.delivery,
                    "pace": reading.pace,
                },
            })
    return cases


def validate_corpus() -> None:
    assert len(CONTRASTS) == 66, len(CONTRASTS)
    cases = build_cases()
    assert len(cases) == 132
    assert len({case["case_id"] for case in cases}) == len(cases)
    for case in cases:
        ir = case["gold_ir"]
        focus = ir["focus_span"]
        if focus is not None:
            assert focus.casefold() in case["target"].casefold(), case["case_id"]
        assert ir["focus_strength"] in (0, 1, 2)
        assert ir["boundary"] in BOUNDARIES
        assert ir["delivery"] in DELIVERIES
        assert ir["pace"] in PACES


validate_corpus()
