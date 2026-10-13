# Multiview Cameras labnotes

This folder contains the formal experimental records for the HoloView and
vehicle-relative camera work. Dispatches and project receipts explain the
story and preserve detail; these notes carry the bounded research claims.

## Completed records

| ID / date | Labnote | Evidence status and primary receipt | Main limitation |
|---|---|---|---|
| 001 · 2026-10-07 | [Bounded HoloView capture in a headless dedicated server](multiview-cameras-001-headless-holoview-capture.md) | Complete, positive; bounded capture bundle and terminal receipt | One camera/output path; no native framebuffer, terrain, or semantic perception claim |
| 002 · 2026-10-07 | [Paired HoloView capture during a bounded vehicle approach](multiview-cameras-002-bounded-vehicle-approach.md) | Complete, positive; paired captures and operation receipts | One bounded approach; not repeatable navigation or a 3D-arrival result |
| 003 · 2026-10-08 | [Sparse terrain-height reconstruction over a stitched vehicle run](multiview-cameras-003-sparse-heightmap.md) | Complete, mixed; 80 operation records and 64 depth captures | Sparse post-hoc map; drive stopped at its attitude limit |
| 004 · 2026-10-13 | [Live multiplayer observation and moving-grid camera tracking](multiview-cameras-004-live-multiplayer-observation-and-moving-grid-follow.md) | Complete, positive; live multiplayer observation ledger and terminal receipt | Human drove; sampled transforms are not a trajectory; saved-grid render only |
| 005 · 2026-10-13 | [Client-visible markers for virtual camera poses](multiview-cameras-005-client-visible-virtual-camera-markers.md) | Complete, positive; marker implementation and client-check receipt | Participant confirmed markers; no saved in-game screenshot or accuracy benchmark |
| 006 · 2026-10-13 | [Operational vision through damage-aware wireframes and normal MCP capture](multiview-cameras-006-operational-vision-and-normal-mcp-capture.md) | Complete, mixed; tool-discovery, damage-wireframe, and normal-capture records | One successful static image call; another session lacked the capture tool; damage view not live-validated |

The publication projection includes only each note and its explicitly
allowlisted assets; raw logs and local fixture records are excluded.

## Follow-up records

Keep later work in separate records when it uses a different fixture,
controller, or evidence source. Planned topics include open-platform GPS
waypoint baselines, depth-guided GPS attempts, future human-driven valley
observations, live damage-view validation, and obstacle-course driving.

Do not combine these into one success narrative. A shared vehicle or camera
does not make the measurements interchangeable.
