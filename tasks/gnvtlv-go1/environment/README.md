# gnvtlv

A small Go CLI for working with Geneve (RFC 8926) packets in the
"decode → resolve → audit" pipeline shape used by our network-side
tooling. The binary lives at `/app/bin/gnvtlv` after `make build`.

## Subcommands

```
gnvtlv decode  --in <file>
gnvtlv resolve --in <file>
gnvtlv audit   --in <file> [--policy /app/configs/audit_policy.json]
```

Each subcommand reads a single packet (raw bytes — not a hex string) and
writes a JSON document to stdout.

## Layout

```
cmd/gnvtlv/        CLI entry point
internal/wire/     bit-field helpers for the 8-byte Geneve fixed header
                   and the 4-byte per-option header
internal/decode/   strict byte-level decoder
internal/resolve/  IANA option-class registry + per-option payload kinds
internal/audit/    cascade + policy engine
internal/policy/   policy.json loader
internal/render/   JSON output writer
docs/              SPECIFICATION.md, CASCADE_RULES.md,
                   CANONICAL_RULES.md, OUTPUT_SCHEMA.md
configs/           geneve_registry.json, ethertype_registry.json,
                   audit_policy.json
testdata/          generated packets
tools/             gen_fixtures.py — regenerates testdata at build time
```

## Reference material

See `docs/SPECIFICATION.md` for the on-the-wire layout, `docs/CASCADE_RULES.md`
for the cross-option propagation rules the auditor enforces,
`docs/CANONICAL_RULES.md` for strictness rules that escalate to errors,
and `docs/OUTPUT_SCHEMA.md` for the exact JSON shape downstream consumers
expect.
