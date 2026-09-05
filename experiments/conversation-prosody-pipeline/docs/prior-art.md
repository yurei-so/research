# Prior art and research context

Conversation Prosody Pipeline sits between speech processing and language-model
reasoning. It preserves measurable properties of a spoken turn—such as timing,
rate, energy, and pitch variation—beside the transcript, then compares them with
the current conversation rather than assigning an emotion or identity.

This note maps the closest research traditions, explains what the project borrows
from each, and states where its own contribution may lie. It is a selective reading
guide, not a complete survey. Links favor original papers, proceedings, and project
pages. Literature was last reviewed on 2026-06-27.

## 1. Classical spoken dialogue systems

Classical spoken dialogue systems were usually pipelines: automatic speech
recognition (ASR) produced words or hypotheses; a language-understanding component
mapped them into intents or semantic frames; a dialogue manager tracked state and
selected an action; and language generation plus text-to-speech produced the reply.

The [Air Travel Information System (ATIS) evaluations](https://aclanthology.org/events/hlt-1990/)
helped make restricted-domain spoken-language systems comparable. Later,
[Galaxy-II](https://www.isca-archive.org/icslp_1998/seneff98b_icslp.html) made the
pipeline explicitly modular: a hub routed messages among recognition, language,
dialogue, database, generation, and synthesis servers. The DARPA Communicator
program adopted that architecture and evaluated multiple travel-planning systems
on shared tasks. Its logged metrics included word error rate, turn counts, task
completion, reprompts, and response latency
([Walker, Passonneau, and Boland, 2001](https://aclanthology.org/P01-1066/)).

Two further ideas matter here:

- [PARADISE](https://aclanthology.org/P97-1035/) treated system quality as a
  combination of task success, dialogue costs, and user satisfaction instead of a
  single component score.
- Statistical dialogue managers represented uncertainty about what the user meant
  and optimized policies over dialogue state. The
  [POMDP review by Young et al. (2013)](https://doi.org/10.1109/JPROC.2012.2225812)
  surveys one influential statistical approach to that problem.

The cited ATIS, Galaxy-II, and Communicator work provides direct precedents for
modularity, explicit interfaces, dialogue state, and whole-dialogue evaluation. In
those papers, the primary representations and evaluation targets center on
recognized linguistic content, task state, task success, and interaction costs.
They do not establish that earlier systems never exposed prosodic metadata; only
that such metadata is not the principal interface described in these examples.

**Takeaway for this project:** the middleware shape is a continuation of the
classical modular tradition, not a new architectural idea by itself. This project's
specific design choice is to make transcript-aligned acoustic and interactional
measurements part of its public interface. This review does not establish that the
choice is unprecedented.

## 2. Prosody and paralinguistics

Prosody covers patterns such as intonation, rhythm, prominence, duration, and
phrasing. *Paralinguistics* is broader and often includes voice quality, loudness,
speaking style, non-verbal vocalizations, and perceived speaker states or traits.
The boundary is not perfectly consistent across fields.

Several findings motivate retaining more than words:

- Prosodic features can help distinguish dialogue acts when the same or similar
  words perform different conversational functions. Work on Switchboard found that
  prosody adds information to lexical models, while also showing that words and
  prosody should be combined rather than treated as competitors
  ([Shriberg et al., 1998](https://arxiv.org/abs/cs/0006024);
  [Jurafsky et al., 1998](https://aclanthology.org/W98-0319/)).
- Turn exchange is tightly coordinated but not mechanically uniform. A ten-language
  study found broad pressure to minimize both silence and overlap, alongside
  language-specific timing differences
  ([Stivers et al., 2009](https://pmc.ncbi.nlm.nih.gov/articles/PMC2705608/)).
  Corpus analysis also shows that pauses, between-speaker gaps, and overlaps have
  different distributions and are sensitive to segmentation choices
  ([Heldner and Edlund, 2010](https://doi.org/10.1016/j.wocn.2010.08.002)).
- Conversational partners may coordinate, or *entrain*, along dimensions such as
  intensity, pitch, and speaking rate. The result depends on which feature, time
  scale, and definition of similarity is used
  ([Levitan and Hirschberg, 2011](https://www.isca-archive.org/interspeech_2011/levitan11_interspeech.html);
  [Levitan et al., 2012](https://aclanthology.org/N12-1002/)).

The following table states interpretation limits adopted by this project; it should
not be read as a set of causal findings from the cited studies:

| Observation | Question it may inform in context | It does **not** establish by itself |
|---|---|---|
| Longer response latency | turn timing and coordination | confusion, reluctance, processing difficulty, or deception |
| Lower RMS energy | a quieter signal or turn-relative change | sadness, confidence, or speaker intent |
| Higher or more variable F0 | intonation and pitch movement | excitement, stress, gender, or identity |
| Slower speech rate | pacing and within-conversation change | fatigue, impairment, or emotional state |
| Overlap or interruption | floor-management dynamics | hostility or rudeness |

Absolute values can be affected by microphone gain, room acoustics, language,
speaking style, physiology, and extraction settings. Conversation-local deltas are
intended to reduce sensitivity to some stable differences, but this benefit has not
yet been demonstrated for the project. Deltas do not by themselves remove channel
effects or make interpretation culturally universal. Even the word *interruption*
can overstate what is, acoustically, just overlapping speech.

**Takeaway for this project:** the cited studies support examining multiple cues and
their temporal context. They do not establish a context-independent map from this
project's feature vector to emotion. The “observations, not conclusions” rule is a
project design constraint; whether it improves safety or response quality remains to
be tested.

## 3. Acoustic feature extraction toolkits

The project does not need to invent pitch tracking, spectral analysis, or standard
voice descriptors. Mature tools already cover those layers:

| Toolkit or standard | Strength | Potential relevance here (project assessment) |
|---|---|---|
| [Praat](https://praat.org/) | Phonetic analysis, annotation, F0, intensity, formants, jitter, shimmer, and scripting | A strong reference implementation for validating individual speech measurements |
| [openSMILE](https://doi.org/10.1145/1873951.1874246) | Configurable real-time and batch extraction of large acoustic feature sets | A practical adapter candidate when broad paralinguistic descriptors are needed |
| [GeMAPS/eGeMAPS](https://doi.org/10.1109/TAFFC.2015.2457417) | A compact, theory-motivated standard parameter set for voice and affective-computing research | A standardized candidate set for cross-study comparison |
| [COVAREP](https://doi.org/10.1109/ICASSP.2014.6853739) | Shared voice-quality and glottal-source implementations intended to improve reproducibility | A candidate for voice-quality experiments, though broader than the current core contract |
| [librosa](https://doi.org/10.25080/Majora-7b98e3ed-003) | Accessible Python primitives for spectral, temporal, and general audio analysis | Convenient for experimental adapters; less speech-specific than Praat or openSMILE |
| [Kaldi](https://publications.idiap.ch/attachments/papers/2012/Povey_ASRU2011_2011.pdf) and [TorchAudio](https://arxiv.org/abs/2110.15018) | Speech/ML pipelines, features, models, and data transforms | Relevant when an adapter shares infrastructure with ASR or learned audio models |

For this project, the main design choice is not “which toolkit wins?” but which
outputs deserve a stable semantic contract. One plausible implementation strategy is
to keep the core dependency-light, define units and aggregation windows precisely,
and test adapters against reference implementations. A standard set such as eGeMAPS
is a reasonable experimental candidate, but copying all of its functionals into
every LLM prompt would increase prompt size; its effect on interpretability and model
performance would require measurement.

**Takeaway for this project:** feature extraction is established prior art. The
project would need to demonstrate value through normalization, turn alignment,
provenance, schema stability, or downstream evaluation—not by presenting familiar
acoustic measures as novel.

## 4. Paralinguistics-aware LLMs

Recent work has connected expressive speech to text LLMs in several ways:

- **Joint text and speech representations.** ParalinGPT combines text with speech
  representations for spoken-dialogue modeling
  ([Lin et al., 2024](https://doi.org/10.1109/ICASSP48485.2024.10446933)). A separate
  Spoken-LLM study trains on paired examples in which similar text spoken in
  different styles receives different responses
  ([Lin et al., ACL 2024](https://aclanthology.org/2024.acl-long.358/)).
- **Learned speech-to-LLM interfaces.** A trained speech encoder can produce tokens
  that make a frozen text LLM respond to linguistic and paralinguistic aspects of an
  utterance
  ([Kang et al., 2024](https://arxiv.org/abs/2410.01162)).
- **End-to-end expressive dialogue.** The Unified Spoken Dialog Model (USDM) learns
  from speech units and generates spoken responses without an explicit ASR/TTS
  cascade
  ([Kim et al., NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/ecfa5340fd896e5314bc5e132b5dd5ca-Abstract-Conference.html)).
- **Explicit annotation at training time.** A 2025 ASRU paper reports gains from
  providing emotion annotations directly and from generating training questions
  using categorical and dimensional emotion annotations
  ([Wang et al., 2025](https://arxiv.org/abs/2508.07273)). This is close in interface
  shape to the present project, but its metadata contains emotion annotations
  rather than only measurements.

The cited systems and datasets cover different tasks and do not support one blanket
claim about the field's data or evaluation setup. AudioBench, for example, separates
speech content, environmental audio, and voice understanding into distinct
evaluation areas
([Wang et al., NAACL 2025](https://aclanthology.org/2025.naacl-long.218/)). Such
benchmarks provide task-specific evidence of capability. This review treats reliable
use of paralinguistic cues across long, natural conversations as an open question,
not as a capability established or disproved by AudioBench.

**Takeaway for this project:** learned audio representations may retain information
that a hand-designed schema omits. Because that information is not exposed as named,
unit-bearing fields, inspecting, normalizing, redacting, or comparing it is less
direct from this project's engineering perspective. Explicit measurements offer a
smaller channel designed for auditability. Whether that channel improves responses
is an empirical question, not something the architecture guarantees.

## 5. Speech LLMs and audio-language models

Speech and audio-language models move the modality boundary inside the model. They
typically connect a speech/audio encoder to an LLM, model discrete audio tokens, or
jointly generate text and speech:

| System | Main contribution | Potential relation to this project (project assessment) |
|---|---|---|
| [SpeechGPT](https://aclanthology.org/2023.findings-emnlp.1055/) | Discrete speech units and cross-modal instruction tuning for speech/text input and output | Reduces reliance on a text-only cascade by handling multiple modalities in one model |
| [AudioPaLM](https://arxiv.org/abs/2306.12925) | Unifies a text LLM with an audio language model for recognition, translation, and speech generation | Its authors report preservation of speaker identity and intonation, cues absent from a plain transcript |
| [SALMONN](https://openreview.net/forum?id=14rn7HpKVk) | Connects speech and general-audio encoders to an LLM for speech, sounds, and music | Broader audio understanding than conversation-specific prosody metadata |
| [Moshi](https://arxiv.org/abs/2410.00037) | A real-time, full-duplex speech-text model that represents both sides of a conversation as concurrent streams | Explicitly models overlap, interruptions, interjections, and low-latency interaction rather than requiring completed turns |

The cited models are designed for tasks beyond ASR, although their demonstrated
capabilities differ. For this project they also present engineering tradeoffs:
model-specific representations, training and inference demands, less direct feature
inspection, and tighter coupling between audio handling and the reasoning model.
Full-duplex work also exposes a limitation of turn-based metadata: reducing a
conversation to completed, isolated turns may lose information about simultaneous
speech and interjections.

**Takeaway for this project:** speech LLMs are both complementary and competitive.
The pipeline is designed to enrich conventional ASR-plus-LLM systems and could serve
as an auditable side channel for evaluating multimodal models; neither benefit has
yet been demonstrated here. If direct-audio models become cheap, reliable, and
inspectable, they may make parts of the pipeline unnecessary. A plausible durable
role is therefore a portable measurement and evaluation layer, not a claim that
structured features outperform learned audio representations.

## 6. How Conversation Prosody Pipeline differs

The project combines familiar ingredients in a deliberately narrow way. The table
is a design comparison, not an exhaustive division of the field: a prior system may
occupy more than one cell, and the cited literature contains exceptions.

| Dimension | Examples in the cited prior art | Conversation Prosody Pipeline design |
|---|---|---|
| Input to reasoning | Transcript, inferred labels, learned speech representations, or combinations of them | Transcript plus named, unit-bearing observations |
| Interpretation | Some systems predict emotion, sentiment, intent, trait, or dialogue act | Defer interpretation to the downstream model and application |
| Reference frame | Utterance features, learned context, or task/dialogue state | Absolute values plus change from a conversation-local running baseline |
| System boundary | Modular pipelines as well as end-to-end speech models | Intended as model- and vendor-agnostic middleware |
| State | Explicit dialogue/task state or learned context | Small, explicit feature baseline scoped to the active conversation |
| Privacy posture | Speaker information may be modeled explicitly or retained in learned representations | Designed not to require a persistent voiceprint or identity profile |
| Inspection | Observable module outputs, predictions, or learned representations | Exposes the exact named observations delivered downstream |

The project is attempting to combine:

1. a small, versioned schema for conversational observations;
2. conversation-relative deltas with visible sample counts;
3. adapters that separate extraction from the middleware contract;
4. explicit avoidance of emotion and identity claims; and
5. planned experiments that measure downstream usefulness, not just feature accuracy.

This review does not establish that the combination is novel, and its usefulness is
not yet validated. The current WAV file and simulated-stream adapters compute
duration, normalized RMS energy, and transcript-derived speech rate; other schema
fields are not yet extracted from real audio. Running-mean deltas may drift, early
turns have weak baselines, and RMS energy may reflect the recording chain more than
the conversation. An LLM may also turn cautious observations back into unwarranted
psychological claims.

The clearest research program is therefore comparative:

- **Transcript-only vs. transcript-plus-metadata:** measure whether metadata changes
  response quality on tasks where vocal delivery matters and should not matter.
- **Absolute vs. conversation-relative features:** test whether deltas improve
  robustness across microphones, speakers, languages, and sessions.
- **Structured features vs. direct audio:** compare with speech-capable models when
  the same model family and evaluation set permit it.
- **Ablation and counterfactual tests:** remove or deliberately alter one feature to
  learn whether the downstream model actually uses it.
- **Calibration and safety tests:** measure false inferences, especially emotion,
  deception, health, personality, and identity claims.
- **Streaming and overlap tests:** evaluate causal windows, baseline updates,
  interruptions, backchannels, and simultaneous speech rather than relying only on
  completed turns.

In short, the project is not a new theory of prosody, a new acoustic toolkit, or an
end-to-end voice assistant. It is an attempt to make a carefully chosen slice of
spoken interaction portable, inspectable, and useful to otherwise text-centered
language-model pipelines. The modesty of that claim is a strength—but only the
comparative experiments above can show whether the slice is the right one.
