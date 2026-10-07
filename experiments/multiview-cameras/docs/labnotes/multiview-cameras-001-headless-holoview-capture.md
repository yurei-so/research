---
schema_version: 1
id: multiview-cameras-001
title: "Bounded HoloView capture in a headless dedicated server"
date: 2026-10-07
status: complete
outcome: positive
question: "Can a headless Space Engineers server export a bounded camera-frame sequence with pose/tick provenance and renderer-side scene context, without native framebuffer access?"
tags: ["space-engineers", "headless-rendering", "camera-observation", "scene-metadata", "provenance", "software-rendering"]
lineage: []
relations: []
publish: true
---
# Multiview Cameras 001: bounded HoloView capture in a headless dedicated server

## Question

Can a dedicated Space Engineers server with no graphical framebuffer produce
an inspectable camera-view sequence whose frames are tied to simulation time
and camera pose, while retaining bounded scene metadata?

## Method

The disposable V2R3 fixture used HoloView 3D's software rasterizer. A bounded
worker-side exporter copied completed RGBA buffers for one selected camera
and LCD surface. A separate assembler validated the frame records, emitted
PNG images and a manifest, and produced a time-lapse whose frame durations
follow the source simulation ticks. The capture was capped by frame count,
exported bytes, raster size, and simulation duration; it did not require a
graphical client or a Steam player session.

Capture `v2r3-20261007-d` from run
`379025977c4081868ddc869f33eda520` emitted 30 frames at source ticks 16
through 3517, at least 120 ticks apart. Each retained raster was 256×256
pixels and was displayed on a 512×512 LCD. Frame records included camera and
output identity, surface index, field of view, camera origin and direction,
source tick, and an image digest. The manifest tied the capture to the run
and terminal server receipt.

Each frame also had a scene-metadata sidecar joined by capture ID, frame
sequence, source tick, camera entity, LCD output, and surface. The bounded
sidecar describes candidate grids/entities and world-space bounds from
HoloView's renderer-frustum inventory; it is not extracted from the raster.
Candidate scanning and serialized-object counts have separate configured
limits, and truncation is recorded rather than silently omitted.

## Result

The bounded single-camera export completed and produced a tick-indexed video,
hashed frames, a capture manifest, and frame-linked scene metadata from the
headless server environment. This is a positive feasibility result for the
specific HoloView software-renderer path.

A separate V2R3 before/after pair provides evidence of differing poses for
the same nominal overhead-drone camera: the captures were about 16 minutes
54 seconds apart, with origins about 19.85 m apart and forward directions
about 28.2° apart. That pair was not a controlled movement trial: no camera
motion was commanded, the field of view and raster resolution differed, and
the earlier camera attribution was sampled at render completion rather than
snapshotted before rasterization.

## Interpretation boundary

This establishes that one selected camera/LCD feed can be sampled and
preserved as a bounded, provenance-linked HoloView software-rendered sequence
on a dedicated server. It does **not** establish that the dedicated server
captured a native framebuffer, that software-rendered pixels are simulator
ground truth, or that every listed scene candidate was visible in the image.
The scene sidecars are renderer-derived context, not pixel detections.

Only one camera/output pair is selected per capture. Simultaneous multiview
capture, cross-camera synchronization, camera-motion control, semantic object
recognition, and navigation competence remain untested. The periodic video
itself is a time-lapse of one feed; it is not evidence that the camera moved.

## Reproduction and source

The bounded capture contract, limits, and verified run details are documented
in the [VRageCage render-trials guide](https://github.com/yurei-so/vragecage/blob/main/docs/render-trials.md).
The implementation is in the [HoloView capture instrumenter](https://github.com/yurei-so/vragecage/blob/main/worker/instrument-holoview-capture.py)
and [frame-video assembler](https://github.com/yurei-so/vragecage/blob/main/worker/holoview-frame-video.py).
The experiment used a disposable instance; source save and Workshop files were
not modified.
