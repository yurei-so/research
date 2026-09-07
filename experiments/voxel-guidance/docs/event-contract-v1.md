# Event contract v1

The Fabric bridge emits newline-delimited JSON. Each line is one complete event
with exactly these envelope fields:

```json
{
  "format": "voxel-guidance.event",
  "version": 1,
  "session_id": "random-experiment-local-id",
  "sequence": 0,
  "observed_at": "2026-09-07T12:00:00Z",
  "instance_id": "Voxel Guidance Lab",
  "task_id": "rehearsal-001",
  "kind": "session_start",
  "payload": {"protocol_id": "rehearsal-v1"}
}
```

Sequences are contiguous and zero-based. Timestamps never move backward. Every
event in a stream has the same session, task, and instance identity, begins with
`session_start`, and ends with `session_end`.

## Event vocabulary

| Kind | Exact payload |
| --- | --- |
| `session_start` | `protocol_id` |
| `position_sample` | numeric `x`, `y`, `z`; `dimension` |
| `inventory_delta` | coarse `category`; nonzero integer `delta` |
| `block_action` | `placed` or `broken`; coarse `category`; positive `count` |
| `damage` | nonnegative finite `amount`; coarse `source_category` |
| `death` | empty object |
| `respawn` | empty object |
| `marker` | one controlled marker name |
| `session_end` | `explicit_stop`, `disconnected`, `completed`, or `crash_recovered` reason |

Unknown envelope or payload fields are rejected. In particular, the contract
has no place for player/account names, chat, server addresses, world names,
screenshots, arbitrary text, or input-device events.

Position samples are raw private apparatus data. The compiler reduces them to
distance and coarse 16-block occupancy cells. It does not export an occupancy
map, retain block contents, or feed a learned spatial tensor.

## Controlled values

- Dimensions: `overworld`, `nether`, `end`.
- Inventory categories: `building`, `resource`, `tool`, `food`, `other`.
- Block categories: `building`, `resource`, `functional`, `other`.
- Damage sources: `environment`, `mob`, `player`, `other`.
- Markers: `plan_started`, `plan_revised`, `setback`, `recovered`,
  `task_complete`.

This vocabulary is intentionally small. Adding a kind, field, or controlled
value requires a new contract version or an explicitly backward-compatible
revision with matching validator and bridge tests.

`stopped` remains accepted for the first three rehearsal streams. New bridge
builds distinguish an explicit `/vg stop` from a neutral `disconnected` event.
Minecraft's managed debug crash can still deliver a disconnect callback, so
`disconnected` deliberately makes no claim about why the connection closed.
