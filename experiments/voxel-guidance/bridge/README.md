# Voxel Guidance Fabric bridge

Client-side Fabric 1.21.1 instrumentation for contract rehearsal. It is inert
until `/vg start <task> <protocol>` is issued or a validated, single-use Prism
Toolkit launch recipe is consumed in its exact toolkit-owned world.

A launch recipe may select `empty`, `construction-kit-v1`, or
`recovery-kit-v1`. The bridge verifies the instance registry, world registry,
world marker, recipe marker binding, private file mode, bounded IDs, and
objective before consuming it. It then clears and applies the preset, resets
day/weather/survival mode, waits for the client inventory to synchronize,
starts recording, and displays the objective. A consumed recipe cannot replay
after reconnecting. Manual commands remain available.

Recipe automation supports bounded elapsed-time, exact inventory-item,
spawn-distance, death/respawn-count, confirmed block-action, `all`, and `any`
predicates. One-shot rules may emit a controlled marker or invoke the single
bounded action `kill_player`. At the declared duration the bridge first writes
and closes an `explicit_stop` boundary, then optionally exits the world or
quits the client. Subjective milestones remain manual markers.

Automatic game quit is accepted only for toolkit-marked ephemeral worlds. The
client receives ten seconds for normal shutdown after the private recorder is
closed; a daemon watchdog then terminates a mod-induced zombie process. World
state may be incomplete by design, but the already-closed recording is intact.

Commands:

- `/vg start <task> <protocol>` — verify toolkit ownership and begin a private
  NDJSON session.
- `/vg marker <name>` — append one controlled marker.
- `/vg status` — show whether recording is active.
- `/vg stop` — append an `explicit_stop` boundary and close the stream.

While active, a `RECORDING` action-bar indicator remains visible. A delivered
disconnect callback closes the session as `disconnected` without guessing its
cause. A hard process termination that cannot deliver that callback leaves the
stream incomplete; analysis rejects it rather than inventing an end event.
The indicator includes elapsed `mm:ss` time for protocol timing.

While recording, the bridge observes one-second position and coarse inventory
snapshots, health/death/respawn transitions, and world-confirmed block
placement/break actions. Output contains controlled categories rather than
exact item names, block names, attackers, or block coordinates.

Build with `./gradlew build`. The remapped mod is
`build/libs/voxel-guidance-bridge-0.2.0.jar` and requires Fabric API.

## Live rehearsal

On 2026-09-07 the bridge built successfully and initialized in the
toolkit-owned `Voxel Guidance Lab` instance with Fabric Loader 0.19.5 and Fabric
API 0.116.17. Recording remained off and no world was opened.

The user's larger mod selection was restored after the isolated check. That
selection currently fails later during Trinkets static-component registration
through the Accessories compatibility stack. This does not implicate the
bridge, but it must be reconciled before an in-world command rehearsal.
