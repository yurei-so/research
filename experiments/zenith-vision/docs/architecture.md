# Architecture

Zenith Vision is an experiment boundary, not a second game client and not yet a
Zenith module. Zenith App owns the live relay, telemetry normalization, service
lifecycle, maps, API integration, and user interface. Zenith Vision may emit
versioned vision evidence for Zenith App to consume later; it does not own a
daemon, a map, or telemetry/vision fusion in production.

```text
MumbleLink relay -- authoritative state --+
                                            +-- observation fusion -- structured context
window-scoped frame -- vision findings ----+
                                                    |
GW2 API / wiki / patch notes -- retrieval ----------+
```

## Authority rules

MumbleLink owns map, position, heading, character, combat state, game build, and
camera pose. Vision may observe UI regions, icons, text, encounter cues, and
other facts unavailable in telemetry. Reserved visual kinds are rejected even
when telemetry is absent or stale: unavailable state must stay unavailable.

The current adapter accepts the `PlayerSnapshot` JSON shape already emitted by
Zenith's relay. Zenith Vision does not copy or control that relay. The live
one-shot runner and fusion helper are lab-only authority tests and must not grow
polling loops, background lifecycle, or a second application backend.

The versioned `zenith-vision.semantic-scene` one-shot contract combines current
MumbleLink world state with allowlisted panel observations. It omits character
identity and withholds source frames, masked frames, and raw OCR text. Missing
or stale telemetry never permits vision to guess world state. The snapshot is
ephemeral output; Zenith Vision still owns no daemon or production lifecycle.

The optional `zenith-vision.interpreted-scene` one-shot contract consumes that
snapshot plus map metadata resolved by Zenith App. It emits only deterministic
situation summaries, a bounded nearest-public-map-reference list, provenance,
and explicit unknowns. It never calls a language model, accepts a prompt, or
fetches ArenaNet directly; Zenith App remains the API policy and cache boundary.

Default HUD geometry is a conservative crop proposal, not detector ground
truth. Training labels must trace the actual visible UI extent on each reviewed
item and carry their own review status.

The independently validated Normal profile at 1920x1080 is promoted only as a
runtime crop heuristic. The crop runtime persists exactly the objectives,
skill-bar, and minimap crops plus a content-free digest receipt; it never writes
the full source frame. Small and Large remain frozen experiment profiles, while
Larger/XL is unsupported. No crop implies a semantic observation until a later
interpreter produces separately verified structured evidence.

The first interpreter is narrowly scoped to locally recognized ordinary game
text from the promoted Normal objectives crop. It emits a private structured
observation with crop digest, backend, confidence, retained/omitted token counts,
completeness, and disclosure-policy provenance. It does not OCR other crops or
the full frame, and identifier-like or insufficiently confident results fail
without output.

The first semantic-vision targets are deliberately small: classify each approved
HUD crop as `present`, `absent`, or `uncertain`, then recognize the allowlisted
Inventory and Hero panel titles in a chat-masked central search area. Transparent
CPU baselines precommit both tasks and their abstention behavior. Synthetic or
single-frame success is plumbing evidence only; no state may be published until
a separately reviewed real holdout meets a frozen promotion gate.

## Experimental progression

1. Contract, privacy, and crop boundaries (complete).
2. UI presence/absence recognition with explicit abstention (current).
3. Held-out recognition of a small predeclared set of UI states and icons.
4. Deterministic advice composition using structured context plus Zenith-owned
   public-map retrieval (one-shot experimental contract complete).
5. Only after measured success: publish a stable vision-evidence contract that
   Zenith may consume.

No phase grants input control. GPU experiments enter through Agent Runtime and
roostd; telemetry normalization and CPU preprocessing do not need an accelerator
lease.

Pixel handling follows the reverse-reveal boundary documented in
[`redaction-boundary.md`](redaction-boundary.md): a new frame begins fully
obscured and only independently approved regions are copied through.
