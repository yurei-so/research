---
schema_version: 1
id: multiview-cameras-002
title: "Paired HoloView capture during a bounded vehicle approach"
date: 2026-10-07
status: complete
outcome: positive
question: "Can the current Voidwright server controller bring a land truck to a defined approach radius while paired onboard and overhead HoloView feeds record the complete bounded trial?"
tags: ["space-engineers", "headless-rendering", "camera-observation", "vehicle-control", "bounded-navigation", "provenance"]
lineage: ["multiview-cameras-001"]
relations: [{"target":"multiview-cameras-001","type":"extends","rationale":"Extends single-camera capture to paired onboard and overhead feeds recorded during a bounded vehicle-control trial."}]
publish: true
---
# Multiview Cameras 002: paired HoloView capture during a bounded vehicle approach

## Question

Can a server-side Voidwright controller bring a land truck into a specified
approach radius while the same run is recorded from onboard and overhead
HoloView views for its full bounded capture window?

## Method

The test used a disposable V2R3 world copy in the headless Magnetar
environment. The source save was not used as the running instance. The Red
Obstacle Course Truck was directed to the GPS target at the bottom of the
ramp, with a 3 m ground-plane arrival radius and a 7,200-tick operation limit.
The current Voidwright working-tree plugin snapshot was staged only in the
disposable instance. No human player client controlled the vehicle.

Two fixed HoloView feeds were recorded together: the truck's onboard camera
and an overhead camera. Each capture was bounded to 7,200 ticks, 120 frames per
view, and 64 MiB of raw output. The recording retained camera pose, source
tick, output identity, per-frame digest, and a renderer-side scene-metadata
sidecar. Each capture produced 119 matched onboard/overhead frame pairs; paired
samples were 6–10 simulation ticks apart. The renderer cadence meant the
120th sample would fall beyond the capture time cap.

The first approach used an older staged plugin snapshot. It reduced target
ground-plane distance from about 20.0 m to 8.2 m, then stalled and ended about
9.0 m away. After staging the current local plugin snapshot, the next bounded
operation continued from the saved position at 0.5 m/s maximum commanded
speed.

## Result

The refreshed controller completed the second operation after 3,436 ticks.
The terminal record reported a 2.999 m ground-plane target distance, inside
the configured 3 m arrival radius, and neutralized the wheels. The full
7,200-tick camera-capture window continued after arrival and ended with both
feeds complete. Across the two successive approaches, target ground-plane
distance fell from about 20.0 m to the configured arrival boundary.

The overhead feed visibly records the truck's movement and approach. The
onboard feed is present in the paired recording but is dark and partly
self-occluded in this fixture. Keeping that weaker view is useful evidence
about the actual camera setup rather than a substituted perspective.

## Interpretation and limits

This is a positive feasibility result for one bounded approach with the
current Voidwright server controller and paired HoloView capture. It
demonstrates a controller-issued movement ending inside the controller's
configured ground-plane radius, with a complete two-view recording and
terminal receipt.

It does **not** establish robust or repeatable autonomous navigation, route
planning around arbitrary obstacles, a physical ramp ascent, or arrival in a
three-dimensional radius. At completion the reported spatial distance was
3.219 m and vertical error was −1.167 m; the controller's arrival condition
was explicitly ground-plane distance. There was one successful continuation,
not a repeated reliability study. The initial attempt stalled, and the two
recordings are sequential bounded operations rather than one uninterrupted
run.

HoloView output is mod-rendered imagery, not native framebuffer capture or
simulator ground truth. Its scene sidecars contain renderer-frustum candidate
metadata, not pixel-derived detections. The camera frames support visual
inspection of this run; they do not independently prove the controller's
terminal state, which comes from the server-side operation receipt.

## Reproduction record

The local trial workspace retains both complete paired recordings, raw frames,
frame manifests, scene sidecars, command records, and terminal receipts under
the Voidwright repository's V2R3 trial artifacts. The successful operation
used the Voidwright server-plugin snapshot and VRageCage HoloView capture
tooling present in the respective working trees at run time. Their staged
plugin tree hashes and capture digests are recorded in the local receipts and
manifests, but the source working trees were not pinned to immutable commits.
The raw media, frames, scene sidecars, commands, and receipts are not included
in this public site projection. This note is therefore a bounded summary, not
a self-contained reproduction bundle.

Related implementation references:

- Voidwright server controller and its bounded actuation contract.
- VRageCage's bounded HoloView capture, paired-frame video assembler, and
  Magnetar terminal receipts.

The source repositories and underlying evidence artifacts require their own
review before they can be published; this note does not expose their working
trees or raw run records.
