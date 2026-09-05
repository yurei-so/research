# Labnote 006: live one-shot observation

## Question

Can Zenith Vision execute its complete live privacy and authority boundary once
against Guild Wars 2 without allowing an optional OCR failure to suppress valid
MumbleLink telemetry?

## Method

- Exact XWayland identity: title, instance, and class revalidated around capture.
- Declared UI profile: independently validated Normal at 1920x1080.
- Persisted vision artifacts: objectives, skill bar, and minimap crops only.
- Full frame: never persisted.
- Objectives OCR: local Tesseract under the operator-approved narrow disclosure
  policy.
- Telemetry: real read-only Proton MumbleLink relay through Zenith's loopback
  backend.
- Private output suppressed recognized text, map/position values, and character
  identity from terminal reporting.

## Result

| Check | Result |
| --- | --- |
| Exact window verified | Pass |
| Three crop artifacts persisted | Pass |
| Full frame persisted | No |
| Objectives OCR | Rejected fail-closed |
| MumbleLink status | Current |
| Map available | Yes |
| Position available | Yes |
| Heading available | Yes |
| Character name persisted | No |
| Fused result persisted privately | Pass |

The first runner revision aborted when objectives OCR retained too little
confident text. The runner was corrected so this optional interpreter contributes
zero visual observations while current authoritative telemetry remains usable.
The repeated live run then completed successfully.

## Decision

- Accept the one-shot live capture, crop, telemetry, and fusion boundary.
- Treat objectives OCR as an isolated optional feature.
- Never substitute visual guesses when telemetry is missing or stale.
- Preserve telemetry-only results when OCR fails closed.
- Improve objectives OCR separately; do not weaken its disclosure threshold to
  manufacture a visual observation.
