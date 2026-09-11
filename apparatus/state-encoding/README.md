# State encoding apparatus

Reusable, deterministic serializers for bounded machine observations. This is
research apparatus rather than an experiment family or a claim that compact
syntax improves model reasoning.

This reusable apparatus is available under the [MIT License](LICENSE).

Version 1 separates three things:

- a schema assigns stable short IDs to typed, human-described fields;
- a snapshot records values, provenance, observation time, and freshness;
- prose, canonical JSON, and compact typed-token views serialize that same
  snapshot.

The compact form is deliberately boring and inspectable:

```text
[v:1][s:2e6c...][t:2026-09-10T12%3A00%3A00Z][src:spectre][ttl:5][bed:0][desk:1]
```

Compact output is not a security boundary. Field IDs are schema-defined, not
secret, and consumers must validate the schema digest before decoding.

```bash
python -m unittest discover -s tests -v
```
