---
schema_version: 1
id: multiview-cameras-006
title: "Operational vision through damage-aware wireframes and normal MCP capture"
date: 2026-10-13
status: complete
outcome: mixed
question: "Can the read-only Voidwright interface expose a damage-aware structural view and an inspectable HoloView image through ordinary Codex MCP tools?"
tags: ["space-engineers", "headless-rendering", "camera-observation", "mcp", "structural-visualization", "provenance", "mixed-result"]
lineage: ["multiview-cameras-001"]
relations: [{"target":"multiview-cameras-001","type":"extends","rationale":"Extends the headless HoloView capture result with an ordinary Codex MCP invocation and a damage-aware structural wireframe path."}]
publish: true
---
# Multiview Cameras 006: operational vision through damage-aware wireframes and normal MCP capture

## Research question

Can the read-only Voidwright interface expose a damage-aware structural view
and an inspectable HoloView image through ordinary Codex MCP tools?

## Validation stages

Two separate disposable runs on 2026-10-13 tested different pieces of the
path. The first examined the live session's tool catalog and a synthetic
damage-colored structural representation. The second established whether a
normal Codex MCP invocation could return an image. They are consecutive
validation stages, not one continuous capture run.

### Stage 1: tool discovery and structural wireframe

The configured read-only adapter advertised the capture tool during a direct
handshake, but the tool catalog injected into one Codex session omitted it.
No substitute capture interface was called, and a stale last-known snapshot
was not presented as current. The fixture remained inactive; no restart was
needed.

The same engineering slice added an optional damage visualization to the
structural wireframe. Observed functional blocks are colored by known damage;
observed nonfunctional blocks are marked separately; unknown or out-of-range
integrity is shown as unknown. Incomplete coverage is labeled unknown, and
absent cells are not called destroyed. Paint, skins, and material appearance
are outside this view.

Build and fixture tests passed, including 18 Agent MCP checks and 29 Core
checks. Damage coloring was verified against synthetic/MCP fixture data, not
a newly acquired live-world damaged grid.

### Stage 2: ordinary Codex image return

In a separate disposable run, the ordinary Codex perspective tool accepted
the enrolled truck's decimal grid identifier as a string and returned that
same identifier. The perspective used a grid-local offset of `(right=0,
up=12, forward=-6)` m and targeted the truck's observed core position. One
normal capture call returned a PNG image block and a structured receipt.

The 256×256 image was nonblank: 209 geometry primitives, 64,677 visible
pixels, and 43 visible colors. Its renderer source was
`holoview-software-render-virtual`. The receipt recorded a structural snapshot
tick and a distinct renderer update counter, and explicitly reported that
they were not simultaneous. Request-to-capture latency was about 98 ms;
snapshot-to-frame age was about 1.9 seconds.

## Result

The normal MCP image-return path succeeded in one bounded invocation, and
the damage-aware wireframe path passed synthetic contract tests. However, one
live session's injected catalog omitted the otherwise configured capture
tool, so availability was not consistent across sessions. The damage-aware
view was not validated against live damage. The result is mixed for
operational vision as a complete, dependable session capability.

## Interpretation and limits

This supports a narrow claim: one ordinary Codex MCP call returned an
inspectable HoloView software render, while the read-only structural tool can
produce a damage-labeled wireframe from available block snapshot fields under
synthetic validation.

It does not establish a streaming video feed, live damage detection, or
native-framebuffer rendering. The HoloView image depicts supported saved-grid
geometry; terrain, avatars, and arbitrary dynamic entities are not established.
Snapshot ticks and renderer counters are separate clocks. The single capture
does not establish sustained cadence, moving-grid following, or reliable tool
catalog refresh.

## Evidence and reproduction

The underlying tool-discovery, damage-wireframe, and normal-capture records
are retained with the experiment. This public note omits machine-local paths,
internal execution identifiers, raw server logs, and full hashes. Both stages
used disposable fixtures; neither changed a production world.
