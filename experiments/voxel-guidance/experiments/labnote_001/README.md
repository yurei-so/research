# Pilot collection runbook

This directory freezes the 12-session pilot. Rehearsals 001–005 are apparatus
tests and must not be copied into pilot inputs.

## World preparation

Create one fresh single-player world for every scheduled session. Name it
`vg-<block>-<task>`, use the block's exact seed, and apply the frozen world
settings. The four worlds within a block share a seed; they are separate saves
so task activity cannot contaminate another condition.

Before recording, set day and clear weather. Empty-inventory tasks begin after
`/clear`. Construction and recovery tasks use `construction-kit-v1`:

```text
/clear
/give @s minecraft:oak_planks 64
/give @s minecraft:cobblestone 32
/give @s minecraft:glass 16
/give @s minecraft:torch 16
/give @s minecraft:oak_door 1
/give @s minecraft:stone_pickaxe 1
/give @s minecraft:stone_axe 1
/give @s minecraft:bread 8
/time set day
/weather clear
/gamemode survival
```

Start with `/vg start vg-<block>-<task> pilot-v1`. Follow the task instruction
and marker definitions in `frozen-protocol.json`. Stop explicitly at eight
minutes with `/vg stop`; sessions under seven or over ten minutes are excluded.

For recovery only, after two minutes:

```text
/vg marker setback
/kill
```

After respawning, mark `/vg marker recovered` only when a viable state has
actually been restored. Complete every block in its frozen order. Do not rerun
or replace a session after seeing compiled results; record interruptions and
apply exclusions before analysis.

