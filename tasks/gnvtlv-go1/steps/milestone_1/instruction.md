There's a small Geneve packet inspector under `/app` — a Go module at `example.com/gnvtlv` exposing a `gnvtlv` CLI with three subcommands (`decode`, `resolve`, `audit`). The packages live under `cmd/gnvtlv` and `internal/`. Sample packets are generated at image build into `/app/testdata` (re-run `python /app/tools/gen_fixtures.py --out /app/testdata` if missing). `/app/docs/SPECIFICATION.md` walks the 8-byte fixed header and the 4-byte per-option TLV; `/app/docs/CANONICAL_RULES.md` lists the strictness codes the decoder must emit; `/app/docs/OUTPUT_SCHEMA.md` pins the JSON shape each subcommand emits.

Right now `go test ./internal/wire/...` and `go test ./internal/decode/...` are not green: the per-option header is being unpacked with the bit fields in the wrong positions, and one of the per-option strictness rules from `CANONICAL_RULES.md` isn't wired into the decoder yet. Make `go build ./...`, `go test ./internal/wire/...`, and `go test ./internal/decode/...` green so `decode` emits option fields that match the wire form.

Note: Go nil slices marshal as JSON `null`. Result-struct slices are initialised with `make([]T, 0)` — keep it that way.

```
cd /app && go build -o ./bin/gnvtlv ./cmd/gnvtlv
./bin/gnvtlv decode --in /app/testdata/two_clean.bin
./bin/gnvtlv decode --in /app/testdata/rbits_nonzero.bin
./bin/gnvtlv decode --in /app/testdata/bare_header.bin
./bin/gnvtlv decode --in /app/testdata/version_one.bin
./bin/gnvtlv decode --in /app/testdata/opt_len_overrun.bin
go test ./internal/wire/... ./internal/decode/...
```
