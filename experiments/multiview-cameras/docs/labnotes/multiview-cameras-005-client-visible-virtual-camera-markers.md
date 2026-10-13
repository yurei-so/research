---
schema_version: 1
id: multiview-cameras-005
title: "Client-visible markers for virtual camera poses"
date: 2026-10-13
status: complete
outcome: positive
question: "Can a connected Space Engineers client display a virtual camera's position and orientation as GPS markers that track a moving vehicle?"
tags: ["space-engineers", "camera-observation", "gps", "client-display", "vehicle-follow", "provenance"]
lineage: ["multiview-cameras-004"]
relations: [{"target":"multiview-cameras-004","type":"extends","rationale":"Extends the live grid-relative camera observation with client-visible GPS markers for the virtual camera pose."}]
publish: true
---
# Multiview Cameras 005: client-visible markers for virtual camera poses

## Question

Can a human client see the position and orientation of a server-side Voidwright
virtual camera while driving, using familiar in-game GPS points?

## Method and correction

The first implementation broadcast a display-only pose packet and expected a
client script to render it. That path failed because the client did not load
the private lab mod; a successful server broadcast did not establish client
visibility.

The display path was changed to the game's built-in server-to-player GPS
replication. For each virtual camera, the client receives three temporary
points: `VW CAM`, `VW LOOK`, and `VW UP`. They are display-only markers; they
do not create a physical entity or issue control commands. Updates are bounded
to a 30-minute live feed, and points are marked stale when updates stop.

The corrected package was staged in a disposable V2R3 fixture. During a human
client session, the server synchronized a camera pose through vanilla GPS
while the Blue Utility Truck was moving.

## Result

The participant confirmed that all three markers appeared and followed the
truck while retaining their relative shape. The server-side pose packet also
changed position and orientation during the session. Together these
observations support that the client-visible points tracked the virtual
camera pose in that session.

## Interpretation and limits

This is a positive client-display check in one disposable fixture and one
human session. It relies on the participant's report; no client screenshot or
video of the GPS list was preserved. The markers represent the virtual camera
pose, not an independently measured optical camera or a physical camera
entity. No truck-control behavior was tested. Stale-marker cleanup and
per-player lifecycle behavior are implemented, but were not fully exercised
by the visual confirmation itself.

## Evidence and reproduction

Build and live-check details are retained in the project's validation
records. This public summary omits machine-local paths, package hashes, and
server logs. The test used a disposable fixture, not a production deployment.
