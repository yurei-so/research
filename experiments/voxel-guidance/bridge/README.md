# Voxel Guidance Fabric bridge

Client-side Fabric 1.21.1 instrumentation for contract rehearsal. It is inert
until `/vg start <task> <protocol>` is issued in a world.

Commands:

- `/vg start <task> <protocol>` — verify toolkit ownership and begin a private
  NDJSON session.
- `/vg marker <name>` — append one controlled marker.
- `/vg status` — show whether recording is active.
- `/vg stop` — append a clean session boundary and close the stream.

While active, a `RECORDING` action-bar indicator remains visible. Disconnecting
closes the session as `stopped`. A process crash leaves the stream incomplete;
analysis rejects it rather than inventing an end event.

Build with `./gradlew build`. The remapped mod is
`build/libs/voxel-guidance-bridge-0.1.0.jar` and requires Fabric API.

## Live rehearsal

On 2026-09-07 the bridge built successfully and initialized in the
toolkit-owned `Voxel Guidance Lab` instance with Fabric Loader 0.19.5 and Fabric
API 0.116.17. Recording remained off and no world was opened.

The user's larger mod selection was restored after the isolated check. That
selection currently fails later during Trinkets static-component registration
through the Accessories compatibility stack. This does not implicate the
bridge, but it must be reconciled before an in-world command rehearsal.

