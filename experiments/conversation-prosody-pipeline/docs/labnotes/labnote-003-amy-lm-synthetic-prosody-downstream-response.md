# Lab note: Amy-LM synthetic prosody downstream-response pilot (v0.3.1)

**Run date:** 2026-07-01  
**Package:** `conversation-prosody-pipeline` 0.3.1  
**Metadata schema:** 1.0  
**Status:** Completed negative/inconclusive pilot; source audio quarantined after provenance audit

> **2026-08-23 provenance correction:** This experiment did not synthesize its input
> audio. It consumed pre-generated WAVs from the named third-party dataset. A later
> audit of every published dataset revision found no synthesis model, voice, prompt,
> seed, generation script, license, or human-validation record. The retained run also
> lacks a source-shard hash and immutable dataset revision. Eight current public rows
> were transcribed as a limited integrity probe: all were closer to `rewritten_text`
> than `original_utterance`, but one automated transcript contained a possible extra
> interjection absent from both stored text fields. Because the current files cannot
> be proven byte-identical to the unpinned July input, that probe does not retroactively
> validate the original run. Treat the corpus audio as provenance-invalid: preserve
> this negative result as history, but do not use its audio for training, validation,
> or further scientific claims. A separately numbered rerun must generate and
> fingerprint audio locally and pass transcript-fidelity and treatment-separation
> gates before downstream response generation.

The software run completed, but correctly matched delivery cues did not outperform
shuffled cues under the available automatic proxies. The result is consistent with
the LLM responding to the presence and style of structured cue text rather than
reliably extracting useful social signal from cue correctness. It does not prove that
mechanism, and human blinded ratings have not been completed.

## Question

Does adding delivery cues derived from the correct audio improve an LLM's response to
flattened conversational text relative to text-only and shuffled-cue controls?

## Setup

This experiment followed the Shakespeare monologue downstream-response pilot. That
pilot validated the prompt and generation plumbing and showed that cue text changes
generation, but theatrical monologues are not conversation turns and matched cues did
not outperform controls. Amy-LM is a bridge experiment using short conversational
utterances paired with synthetic speech.

The inspected local shard of
`hungphongtrn/amy-lm-synthetic-prosody-speech-dataset` contains one `train` split with
200 rows and these fields:

- `dialog_id`
- `original_utterance`
- `rewritten_text`
- `emotion`
- `speech_act`
- `intent`
- `audio`

Audio is embedded mono 24 kHz PCM WAV. The runner converts selected audio to mono
16 kHz PCM WAV before analysis. The available parquet metadata did not state a
license. A programmatic Hub metadata request failed because DNS was unavailable, so
the dataset license and revision remain missing or unclear. The provenance and human
validation status of the dataset-provided labels were not established. A later audit
established that the dataset card contains schema metadata only and does not disclose
how the audio was synthesized.

Reproducibility details:

- Repository commit at experiment start:
  `4a71808a5c784b0973cb2e31522373ad6eedb33b`
- Runner SHA-256:
  `7d01130e3e1dd589916096c4afa438c599b19d84a78e9509e4d4dc43e8f7380a`
- Requirements SHA-256:
  `f9c20bbacbe424aad1c575c7c1946f57d20b16da5cce3b4a8d807ef8e720a019`
- Python: 3.13.5
- `datasets`: 4.8.5
- NumPy: 2.5.0
- SoundFile: 0.14.0
- FFmpeg: 7.1.5
- Ollama model: `qwen2.5:3b`, local ID `357c53fb659c`
- Generation: temperature 0.4, seed 42, non-streaming chat completion
- Dataset revision and source-shard hash: not available in the retained run metadata
- Audio synthesizer, voice, conditioning, prompt, seed, and generation code: unknown

The same system prompt was used for every response:

> You are speaking naturally with this person. Respond as a supportive
> conversational companion. Do not summarize what they said. Instead, continue the
> conversation naturally while respecting the speaker's emotional state, confidence,
> uncertainty, pacing, and conversational intent.

## Method

The bounded run processed the first 20 rows of the inspected shard. For each row, the
runner:

1. extracted the embedded WAV and converted it to mono 16 kHz PCM;
2. passed the WAV and rewritten text to `ingest_wav_file`;
3. built schema 1.0 output through a fresh `ProsodyPipeline`;
4. calculated experiment-local internal-pause, pitch-variability, and
   energy-variability observations;
5. converted numeric observations into compact qualitative-plus-numeric cue text;
6. generated five prompt conditions with identical model settings; and
7. wrote master, randomly ordered blinded, and separate answer-key JSONL artifacts.

The package supplied duration, normalized RMS energy, and transcript-derived speech
rate. Experiment-local analysis supplied internal-pause count, mean and maximum
internal pause, pitch variability, and energy variability. These are descriptive
measurements, not emotion inference. No raw JSON or experiment-condition language was
shown to the response model.

The five conditions were:

- **A — original utterance only:** expressive dataset text.
- **B — rewritten text only:** flatter semantic text.
- **C — rewritten text plus matched cues:** compact cues from that row's audio.
- **D — rewritten text plus shuffled cues:** the next processed row's complete cue
  bundle, wrapping at the end as a deterministic derangement.
- **E — rewritten text plus gold labels:** dataset emotion, speech-act, and intent
  labels as an approximate upper-bound control.

The rewritten text reduces some lexical emotional leakage and gives delivery cues more
room to matter. The shuffled control tests whether correctly matched cues help more
than merely adding plausible structured text. Condition E is not a fair production
condition.

## Results

All 20 selected rows completed with no reported processing failures. The run produced
100 prompts, 100 responses, 100 master evaluation rows, 100 randomly ordered blinded
rows, and a separate 100-row answer key.

| Condition | Mean response words | Explicit cue-language responses |
|---|---:|---:|
| A: original only | 45.25 | 0/20 |
| B: rewritten only | 42.75 | 0/20 |
| C: rewritten + matched cues | 59.35 | 0/20 |
| D: rewritten + shuffled cues | 51.60 | 2/20 |
| E: rewritten + gold labels | 51.35 | 0/20 |

Mean token-set Jaccard similarity was 0.204 for A versus B, 0.263 for B versus C,
0.300 for B versus D, and 0.286 for C versus D. Both matched and shuffled cue blocks
changed response wording relative to rewritten text alone. Matched cues produced
longer responses on average, but response length and lexical change are not measures
of conversational quality or correct cue use.

A follow-up position-free embedding sanity check compared C and D with the expressive
original and with the dataset's emotion-plus-intent text:

| Reference | C wins | D wins | Mean C similarity | Mean D similarity | Paired permutation p |
|---|---:|---:|---:|---:|---:|
| Expressive original | 9 | 11 | 0.7296 | 0.7332 | 0.814 |
| Gold emotion + intent | 13 | 7 | 0.5235 | 0.5181 | 0.569 |

Neither comparison provides evidence that C outperforms D. The gold-reference result
moves slightly toward C, but the difference is small and compatible with chance in
this sample.

The shuffled intervention was not trivially identical to the matched intervention.
Only 2 of 20 C/D pairs shared at least 75% of their qualitative cue lines, and no pair
had an identical cue bundle.

A local LLM pairwise judge was also attempted with randomized C/D display order and
schema-constrained output. Its preference result was rejected because the judge chose
the second displayed candidate in 33 of 40 trials and marked all decisions high
confidence. D won only 5 of 18 trials when displayed first but 20 of 22 when displayed
second. This is a position-bias diagnostic, not evidence for either condition.

## Interpretation

Compact delivery cues clearly changed model behavior: C was longer and lexically
different from B. That observation alone does not show that the model used the cues
correctly. D also changed behavior, and C did not beat D on either position-free
automatic alignment proxy.

The cautious interpretation is therefore:

> In this synthetic single-turn dataset, compact delivery cues changed model behavior,
> but matched cues did not outperform shuffled cues under automatic proxies. This is
> consistent with the tested LLM responding to the presence and style of structured
> cue text rather than extracting usable social signal from cue correctness.

“Consistent with” is important. The run does not isolate the model's internal
mechanism, automatic similarity is a weak quality measure, and the experiment does not
show that delivery information is generally useless. It shows that this cue
representation, model, and evaluation did not demonstrate correct cue use.

## Interpretation limits

- Synthetic speech may not generalize to human speech.
- Short single turns do not test conversation-local or multi-turn adaptation.
- The first 20 rows are a small, non-random sample.
- Gold labels are dataset-provided and may not be human-validated.
- One 3B model, one generation per condition, and one seed are insufficient.
- Lightweight pitch, pause, and energy estimates are not validated affect measures.
- Speech rate uses rewritten text over the original audio duration.
- Qualitative cue bins are generic rather than speaker-calibrated.
- Embedding and lexical metrics measure similarity or change, not empathy,
  naturalness, or pragmatic appropriateness.
- The attempted LLM judge had severe display-position bias and was discarded.
- Human blinded ratings have not been completed.
- Dataset license and revision were unavailable during the run.
- The source audio has no reproducible generation provenance and is quarantined from
  reuse; therefore even “matched” means only “same dataset row,” not a validated match
  between label, intended delivery, and synthesized realization.

## Next steps

1. Do not spend human-rating labor on this quarantined corpus.
2. Recreate the bounded experiment with locally generated, fingerprinted
   whole-utterance audio and explicit fidelity/separation gates.
3. Use same-text/different-delivery audio so lexical content is exactly controlled.
4. Add deliberately contrasting or anti-correlated cue bundles to increase treatment
   separation and test whether responses move in the predicted direction.
5. Calibrate qualitative cues against a speaker or dataset baseline.
6. Repeat with a stronger local model, multiple seeds, and a position-balanced judge
   only after validating the judge on known-answer controls.
7. Move to multi-turn human conversation data after the bridge experiment, subject to
   licensing and annotation review.

## Bottom line

The run validates the historical five-condition plumbing and shows that compact cue
text changes generation. Its opaque source audio prevents stronger scientific reuse.
It does not provide evidence that the model uses correctly
matched delivery cues more effectively than plausible shuffled cues. The current
evidence is consistent with sensitivity to structured cue text, not demonstrated use
of cue correctness.
