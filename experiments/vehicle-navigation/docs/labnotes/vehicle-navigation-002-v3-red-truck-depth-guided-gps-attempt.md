---
schema_version: 1
id: vehicle-navigation-002
title: "V3 Red Truck depth-guided GPS attempt"
date: 2026-10-09
status: complete
outcome: mixed
question: "Can the V3 Red Truck's depth-guided controller reach the End Position GPS within a bounded low-speed operation?"
tags: ["space-engineers", "vehicle-control", "depth-guidance", "gps-waypoints", "bounded-navigation", "mixed-result"]
lineage: ["vehicle-navigation-001"]
relations: [{"target":"vehicle-navigation-001","type":"motivated-by","rationale":"Tests a different controller and fixture after the V2 open-platform GPS waypoint baseline; this is not a direct replication."}]
publish: true
---
# Vehicle Navigation 002: V3 Red Truck depth-guided GPS attempt

## Question

Can the V3 Red Truck use its front depth camera and bounded controller to
reach the `End Position` GPS within a low-speed operation window?

## Method

The run used a disposable V3 planetary fixture, vehicle `[Voidwright] Red
Truck`, its front depth camera, and the `End Position` GPS target. The
controller was capped at 0.5 m/s and 1,800
simulation ticks (30 nominal seconds), with a 3.1 m arrival radius. No human
player controlled the truck during the operation.

## Result

The operation timed out without reaching the target. Ground-plane target
distance fell from 77.857 m to 68.520 m, and the position-derived path and
center-of-mass displacement were 10.175 m and 10.125 m. The terminal sample
reported a clear scan, 8 m minimum corridor clearance, data four ticks old,
and no self-grid hits. Final position-derived speed was 0.521 m/s; the engine
reported 0.354 m/s.

This is a mixed result: the controller produced measurable progress with a
clear final depth sample, but did not arrive before its time limit.

## Interpretation and limits

The 9.337 m reduction in controller-reported target distance is not an arrival or course
completion. A clear corridor sample at the terminal point does not prove the
whole route was clear. The small difference between the commanded 0.5 m/s cap
and terminal position-derived speed, together with the lower engine-reported
speed, merits measurement before treating the cap as a hard physical ceiling.

The method used VRageCage's local lab CLI to exercise the server
plugin/controller path. The MCP adapter build and tests passed, but this trial
was not invoked through a live MCP client; its automated integration tests
used a fake CLI. An older Blue Truck receipt in the fixture reported
`complete` after only 0.145 m path and 0.036 m COM displacement with the target
already about 0.5 m away; it is not evidence of meaningful movement and is
excluded from this result.

## Reproduction and evidence

The terminal operation receipt records the bounded attempt. It changed only
the disposable fixture copy; the source world was not used. This public
summary omits internal execution identifiers and machine-local paths.
