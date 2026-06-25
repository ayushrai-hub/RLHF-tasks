Now that the decoder is honest about the wire form, `gnvtlv resolve` should attach IANA context to every option. It currently emits every option with `recognized: false` and an empty `name`/`kind`. The registries live at `/app/configs/geneve_registry.json` (option class + type → name + payload kind) and `/app/configs/ethertype_registry.json` (inner Ethertype → name). The exact shape the resolver must produce is in `/app/docs/OUTPUT_SCHEMA.md`, and the per-kind helpers are already in `internal/resolve/kinds.go`.

Wire up `resolve.Resolve` so it: looks up each option in the Geneve registry; sets `name`, `kind`, `recognized`, and `decoded` accordingly; resolves the fixed header's `protocol_type` against the Ethertype registry to fill `protocol_type_name`; and emits an `OPT_LENGTH_MISMATCH` resolver issue when a known fixed-size kind disagrees with the actual payload length. Make `go test ./internal/resolve/...` green without regressing milestone 1.

```
cd /app && go build -o ./bin/gnvtlv ./cmd/gnvtlv
./bin/gnvtlv resolve --in /app/testdata/two_clean.bin
./bin/gnvtlv resolve --in /app/testdata/unknown_crit.bin
./bin/gnvtlv resolve --in /app/testdata/length_mismatch.bin
./bin/gnvtlv resolve --in /app/testdata/rbits_nonzero.bin
./bin/gnvtlv resolve --in /app/testdata/kinds_dispatch.bin
./bin/gnvtlv resolve --in /app/testdata/unregistered_ether.bin
go test ./...
```
