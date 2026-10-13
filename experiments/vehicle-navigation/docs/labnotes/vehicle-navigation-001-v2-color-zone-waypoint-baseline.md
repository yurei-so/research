---
schema_version: 1
id: vehicle-navigation-001
title: "Repeated V2 color-zone waypoint baseline"
date: 2026-10-09
status: complete
outcome: positive
question: "Can the V2 Blue Utility Truck repeatedly reach the four color-zone GPS targets and return to Safe Spawn on the open proving-ground platform using bounded wheel guidance?"
tags: ["space-engineers", "vehicle-control", "gps-waypoints", "bounded-navigation", "baseline", "provenance"]
lineage: []
relations: []
publish: true
---
# Vehicle Navigation 001: repeated V2 color-zone waypoint baseline

## Question

Can a land truck complete repeated GPS waypoint legs across the V2 open
proving-ground platform using the existing bounded wheel-guidance controller?

## Method

The trial used a disposable imported V2R3 fixture and its `[Voidwright] Blue
Utility Truck`. One warm-up
approach to Safe Spawn was followed by ten legs: two Safe Spawn ↔ Yellow
round trips, then Safe Spawn ↔ Red, Green, and Blue round trips. Each one-shot
command used a 1 m/s speed cap, 3 m gravity-plane arrival radius, and 7,200
simulation-tick ceiling. The server was cleanly stopped after each leg before
the next command. No manual steering or in-run intervention was used.

## Result

All ten color-zone legs completed inside the configured 3 m ground-plane
radius. Across them, the receipts report about 634.689 m of position-sampled
path and 626.823 m of center-of-mass displacement over 39,402 simulation
ticks (656.7 nominal seconds). Terminal physics speed ranged from 0.031 to
0.106 m/s. Each leg had a passing terminal receipt, with no target fatal
markers; the fixture edit count remained zero for the six additional
Red/Green/Blue receipts.

This is a positive repeatability baseline for waypoint control on this open
platform.

## Interpretation and limits

The trial establishes repeated arrival at GPS targets under the controller's
gravity-plane metric. It does not establish three-dimensional marker
coincidence: Safe Spawn's marker is elevated, and the truck ended about 6.77 m
away in 3D while inside the configured 3 m ground-plane radius. The color-zone
endpoints were about 3.08–3.09 m away in 3D.

The platform legs do not test obstacle avoidance, collision-free operation,
stuck recovery, overshoot recovery, or a full obstacle course. No receipt
records collision contacts. These runs used standard GPS wheel guidance, not
the front-camera depth controller. The successful result must not be
generalized to the separate V2 obstacle-course task.

## Reproduction and evidence

Per-leg distances, timing, path length, COM displacement, speeds, and limits
were retained in terminal receipts. The source save and a separate V2R3 demo
fixture were left untouched. This public summary omits local paths and
machine-specific fixture identifiers.
