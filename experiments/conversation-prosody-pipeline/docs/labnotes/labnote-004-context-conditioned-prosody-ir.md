# Lab note: Context-conditioned prosody IR inference and synthesis

**Run date:** 2026-08-13

**Package:** `conversation-prosody-pipeline` 0.3.1

**Status:** Completed inference and oracle-synthesis run; listener evaluation pending

**Execution host:** `mpaiServer-8kl`

## Question

Can a language model infer an intended, backend-independent prosodic structure from
discourse context when the literal target utterance is held fixed? Separately, can a
Kokoro compiler render that structure so a listener can recover the intended reading?

## Motivation

Labnotes 002 and 003 showed that adding structured delivery cues changes downstream
language-model responses, but correctly matched cues did not outperform shuffled cues
under the available automatic proxies. They therefore did not demonstrate that a
model uses correct prosodic information.

This experiment controls lexical content directly. Each base target appears in two
authored discourse conditions that require different delivery. It also separates IR
inference from synthesis so a reasoning failure is not confused with a TTS realization
failure.

## Preregistered stages

1. **IR inference:** context plus an unchanged target is mapped to a closed prosody
   schema.
2. **Backend calibration:** candidate compiler operations are checked for measurable
   acoustic effects.
3. **Oracle synthesis:** gold IR is compiled independently of model predictions.
4. **End-to-end synthesis:** selected model predictions are compiled only after the
   oracle path passes calibration.

The initial IR contains:

- an optional exact target `focus_span`;
- ordinal `focus_strength` from 0 through 2;
- `boundary` as none, continuation, or final;
- a closed `delivery` category; and
- relative `pace` as slow, normal, or fast.

Categorical delivery is recorded for inference evaluation but is not automatically
translated into an unsupported TTS emotion control.

## Corpus

The authored corpus contains 66 base utterances and two discourse-conditioned readings
per utterance, producing 132 cases across 11 phenomena:

- contrastive emphasis;
- correction;
- certainty;
- genuine versus rhetorical questions;
- continuation versus final boundaries;
- parenthetical prominence;
- interruption;
- sarcasm versus sincerity;
- excited versus serious delivery;
- information structure; and
- pace.

Every focus annotation must be an exact contiguous substring of the unchanged target.
The corpus contains no downloaded media and is tracked with the experiment source.

## Stage A: inference matrix

The preregistered inference matrix is:

- 132 cases;
- three local Ollama models: `qwen3:8b`, `gemma3:12b`, and `llama3.2`;
- three prompt formulations: direct, contrastive, and conservative; and
- five seeds: 101, 211, 307, 401, and 503.

This produces 5,940 trials. The frozen run manifest records exact Ollama model digests,
prompt and corpus hashes, generation settings, Python version, and host platform.

The primary inference outcomes are:

- schema and semantic validity;
- per-field accuracy;
- complete IR exact match;
- whether predictions differ between the paired contexts; and
- whether fields that differ between gold paired readings move in the correct
  direction.

Semantically inconsistent but structurally valid outputs are retained as model errors;
they are not silently normalized or discarded. Proportions are reported with Wilson
95% confidence intervals.

## Stage B: oracle synthesis matrix

The planned oracle matrix contains:

- 132 cases;
- neutral, gold-IR, and sibling-swapped-IR conditions; and
- two Kokoro voices, `af_heart` and `am_adam`.

This produces 792 clips. The initial compiler limits itself to localized focus gain
over Kokoro-aligned token timestamps, relative pace, and punctuation-based boundary
handling. Each unique text/voice/speed base waveform is cached and reused across
conditions so repeated synthesis variation cannot masquerade as an IR effect. The
swapped condition applies the other discourse reading's gold IR to the same literal
target and tests whether any
observed effect follows the intended structure rather than merely the presence of
extra processing.

Kokoro runs on CPU for this experiment. The isolated environment resolved PyTorch
2.13.0, whose CUDA build requires a newer NVIDIA driver than the host currently has;
changing the working host driver is outside this experiment's scope. Kokoro's small
82M-parameter model remains practical on CPU, while Ollama retains exclusive GPU use.

Automated duration, RMS, segment, and artifact-integrity observations are diagnostic.
The eventual primary realization outcome is blinded listener recovery of the intended
discourse reading; naturalness is secondary.

## Execution and recovery

Both phases use native systemd user services on `mpai`, not an interactive SSH process.
Inference results are committed individually to a WAL-mode SQLite ledger. A terminated
service resets only an in-progress task and skips every completed task on restart.
Generated ledgers, audio, exports, and model files remain under ignored `artifacts/`
or host-local caches rather than entering Git.

The synthesis service runs with Hugging Face Hub and Transformers offline modes
enabled after a successful two-voice cache warm-up and fingerprint pass. A detached
12-clip offline smoke matrix completed without failures, demonstrating that synthesis
does not require DNS or model-hub access during the experiment.

The production Agent Runtime scheduler and its CodeCat worker were intentionally
stopped and disabled before the run so they cannot contend for model resources.
The separate Agent Companion service remained active.

## Results

Both detached phases completed without failed tasks or service restarts:

| Phase | Completed | Failed |
|---|---:|---:|
| IR inference | 5,940/5,940 | 0 |
| Oracle/control synthesis | 792/792 | 0 |

All 792 recorded WAV paths existed after the run and every file matched its ledger
SHA-256. No inference task required a retry. The completed systemd units were disabled
after verification so a later host reboot cannot replay the successful handoff.

### Inference

The best complete-IR result came from Gemma 3 12B with the conservative prompt:

| Metric | Result | Wilson 95% CI |
|---|---:|---:|
| Semantic validity | 89.1% | 86.5–91.2% |
| Exact IR match | 15.6% | 13.0–18.6% |
| Paired prediction changed across contexts | 92.4% | 89.1–94.8% |
| Paired directional contrast correct | 23.3% | 19.1–28.2% |
| Both readings exact within a pair | 9.4% | 6.7–13.0% |

Its per-field accuracy was 92.6% for boundary, 76.8% for delivery, 84.4% for pace,
47.3% for focus strength, and 31.7% for the exact focus span. The contrastive prompt
improved Gemma's focus-span accuracy to 44.1% and semantic validity to 100%, but reduced
delivery accuracy and complete-IR exact match.

Aggregate results across all prompts were:

| Model | Semantic validity | Exact IR match |
|---|---:|---:|
| Gemma 3 12B | 90.2% | 14.1% |
| Qwen 3 8B | 99.5% | 6.3% |
| Llama 3.2 | 70.6% | 3.0% |

Of 5,940 structurally valid JSON results, 786 (13.2%) violated a semantic invariant,
usually by pairing a null focus span with nonzero focus strength or by selecting text
that was not an exact target substring. These were retained as experimental errors.

The context clearly affected generation: depending on configuration, 92.1–98.5% of
paired predictions differed. That sensitivity was not reliably correct. Directional
paired accuracy ranged from 3.0% to 23.3%, and complete-pair exact match ranged from
0% to 9.4%.

The best configuration was also highly phenomenon-dependent. It achieved 91.7% exact
match for the authored boundary cases and 40.0% for correction, but 0% for affect,
certainty, pace, and parenthetical cases. This exposes a limitation in treating the
entire closed IR as equally inferable: straightforward discourse-boundary distinctions
were much easier than intended affect, epistemic stance, or pacing.

### Synthesis

The final oracle matrix used cached base waveforms and a localized gain operation over
Kokoro-aligned focus timestamps. In the focus calibration pair, neutral, gold, and
swapped clips had exactly equal duration, and gold/swapped RMS effects exchanged when
the focus span exchanged. This removed the large segment-splicing duration confound
found in an earlier smoke compiler.

Across the full matrix, aggregate gold and swapped summaries were identical by design:
each paired reading receives each sibling IR once. Mean durations were 2.405 seconds
for `af_heart` and 2.583 seconds for `am_adam`; neutral means were 2.371 and 2.547
seconds respectively. The remaining difference arises from intended pace and
punctuation-based continuation controls on cases where the gold/swapped rendering is
not the neutral rendering.

These acoustic diagnostics demonstrate that the compiler produced bounded,
integrity-checked interventions. They do **not** establish that those interventions
communicate the intended meaning. Gold-versus-swapped listener identification remains
the required realization test.

## Interpretation

The Stage A answer is mixed but informative:

> Local models strongly respond to discourse context when assigning prosody, but the
> tested models and prompts do not reliably recover the complete authored prosody IR.
> Boundary intent is promising; exact focus placement and higher-level delivery
> distinctions remain the main inference bottlenecks.

The run therefore rejects a simple assumption that context sensitivity implies correct
prosodic reasoning. It also provides a reproducible corpus and error decomposition for
improving the representation or prompting without conflating those changes with TTS
behavior.

Stage B remains open until blinded listeners classify gold, swapped, and neutral audio.
No claim about successful semantic realization should be made from RMS or duration
differences alone.
