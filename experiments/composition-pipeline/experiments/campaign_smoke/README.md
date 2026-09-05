# Campaign contract smoke

This CPU-only campaign expands a small fixed matrix, writes a private resumable
checkpoint, and emits a sanitized summary. It exists to validate campaign
infrastructure without contacting a model or acquiring accelerator capacity on
its own.
