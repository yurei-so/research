# Real-Time Application Integration

This note outlines how an external application can stream live audio into
Conversation Prosody Pipeline (CPP), combine it with speech-to-text output, and
send the resulting observations to a language model.

The first real-time milestone is deliberately turn-based: audio is ingested as it
arrives, but structured metadata is emitted only after the current turn and its
transcript are complete. Continuously revised, provisional metadata is outside
this initial scope.

## Application Shape

A speech-to-text service usually consumes audio and returns text; it does not pass
the original audio onward. The application therefore needs to send the same audio
frames to both speech-to-text (STT) and CPP.

```text
                         +--> STT --> transcript + turn timing --+
Microphone --> PCM tee --+                                     +--> CPP
                         +--> CPP audio stream -----------------+
                                                                 |
                                                                 v
                                                       structured turn JSON
                                                                 |
                                                                 v
                                                        prompt assembler
                                                                 |
                                                                 v
                                                               LLM
                                                                 |
                                                                 v
                                                             response
```

CPP remains middleware in this arrangement. It does not need to own microphone
capture, speech recognition, voice activity detection, networking, prompt design,
or language-model inference.

## Turn Lifecycle

For each conversation, the external application creates one conversation-local
CPP session. For each user turn, it:

1. starts a streaming turn with a stable turn identifier and PCM format;
2. sends each microphone audio frame to both STT and CPP;
3. uses an upstream STT or voice-activity-detection signal to determine when the
   turn ends;
4. obtains the final transcript and timing from STT;
5. finalizes the CPP turn with that transcript and timing;
6. receives structured metadata containing measurements and conversation-relative
   deltas; and
7. gives the transcript and, when desired, the metadata to the downstream LLM.

A prospective application-facing API could look like this:

```python
cpp = ProsodySession()

while conversation_active:
    turn = cpp.start_turn(
        turn_id=turn_id,
        audio_format=PCMFormat(
            encoding="pcm_s16le",
            sample_rate=16_000,
            channels=1,
        ),
    )

    async for pcm_chunk in microphone_turn():
        stt.push_audio(pcm_chunk)
        turn.push_audio(pcm_chunk)

    transcript = await stt.finalize()
    metadata = turn.finish(
        transcript=transcript.text,
        timing=transcript.timing,
    )

    response = await llm.generate(
        transcript=transcript.text,
        prosody=metadata.to_dict(),
    )
```

This is a design sketch rather than the current public API. The implementation
should remain synchronous and transport-neutral at its core; an asynchronous
application can call it from its own capture or networking loop.

## Stream Contract

The initial stream contract should make the following properties explicit:

- The PCM encoding, sample rate, and channel count are established when the turn
  begins rather than repeated on every chunk.
- Duration is derived from received PCM frame counts rather than trusted from the
  caller.
- Sequence numbers or frame offsets allow gaps, duplicates, and reordered chunks
  to be detected.
- Finalization is an explicit operation rather than a flag attached to the last
  audio chunk.
- Audio completion and transcript availability are separate events.
- A turn can be finalized only once, and no more audio can be added afterward.
- Conversation baselines are updated only by finalized turns.
- Session lifetime and reset behavior are explicit so separate conversations do
  not share baseline state.

Turn boundaries should initially come from the external application. Adding voice
activity detection to the CPP core would couple the middleware to a particular
segmentation strategy and dependency stack.

## Example Output

After a turn is finalized, CPP may produce metadata shaped like:

```json
{
  "schema_version": "1.0",
  "turn_id": "turn-17",
  "transcript": "Yeah... I'm fine.",
  "timing": {
    "start_ms": 12400,
    "end_ms": 14620,
    "duration_ms": 2220
  },
  "features": {
    "duration_ms": 2220,
    "speech_rate_wpm": 98,
    "energy_rms": 0.21
  },
  "deltas": {
    "absolute": {
      "speech_rate_wpm": -34,
      "energy_rms": -0.12
    },
    "relative": {
      "speech_rate_wpm": -0.26,
      "energy_rms": -0.36
    }
  },
  "baseline_sample_count": 4
}
```

`turn_id` is prospective and is not part of the current metadata schema. Its exact
placement should be decided as part of the real-time contract.

The prompt assembler, not CPP, decides how to present these fields to the language
model. A human-readable rendering might be:

```text
User transcript:
"Yeah... I'm fine."

Measured delivery metadata:
- Speaking rate: 98 WPM, 26% below the conversation baseline
- RMS energy: 0.21, 36% below the conversation baseline
- Turn duration: 2.22 seconds

Treat these as acoustic observations, not evidence of any particular emotion,
intent, health condition, personality trait, or identity.
```

## Transport Boundary

The reusable core should accept stream events without depending on WebSocket,
gRPC, microphone, or STT libraries. External adapters can translate their native
events into that contract:

```text
WebSocket / gRPC / application SDK
                 |
                 v
     transport-neutral stream API
                 |
                 v
      streaming turn accumulator
                 |
                 v
       ProsodyPipeline finalization
```

A reference network adapter can be added after the lifecycle and validation rules
are stable. Keeping that adapter outside the core preserves the project's small,
dependency-free middleware boundary.

## First Downstream Experiment

The first planned experiment compares responses from an off-the-shelf language
model without fine-tuning:

```text
Control:   transcript                --> same LLM --> response
Treatment: transcript + CPP metadata --> same LLM --> response
```

Both conditions should use:

- the same source audio and final transcript;
- the same model, system prompt, conversation history, and sampling settings;
- the same CPP baseline state, with metadata computed for both conditions but
  withheld from the control; and
- deterministic generation or multiple runs per condition to account for response
  variation.

Evaluation should include cases where vocal delivery is relevant and cases where
it should not affect the answer. This tests both whether structured observations
can improve a response and whether they encourage unwarranted conclusions. A
quieter signal, slower speaking rate, or longer pause must not be treated as proof
of an emotion, intention, health condition, or personality trait.

The current dependency-free implementation can begin this experiment with turn
duration, normalized RMS energy, and transcript-derived speech rate. Additional
features and provisional during-turn output can be evaluated separately after the
turn-final integration path is reliable.
