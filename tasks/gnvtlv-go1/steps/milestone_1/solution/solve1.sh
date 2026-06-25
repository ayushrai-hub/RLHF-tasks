#!/bin/bash
set -euo pipefail
cd /app

echo "==> survey the project layout"
ls -la /app
ls /app/cmd/gnvtlv /app/internal
echo "==> read the relevant spec sections"
sed -n '38,68p' /app/docs/SPECIFICATION.md
sed -n '18,33p' /app/docs/CANONICAL_RULES.md
echo "==> inspect the current per-option header parse"
grep -n 'RBits\|LengthWord' /app/internal/wire/wire.go
echo "==> inspect the per-option loop in the decoder"
grep -n 'pos += wire.OptionHeaderLen\|OPT_R_BITS\|OPT_PAYLOAD_OVERRUN' /app/internal/decode/decode.go || true
echo "==> patch wire.go RBits / LengthWord bit positions and add the R-bits check in decode.go"

python - <<'PYEOF'
import pathlib

wire_path = pathlib.Path("/app/internal/wire/wire.go")
wire_src = wire_path.read_text()
bad_r = "\t\tRBits:      b[3] & 0x07,"
bad_l = "\t\tLengthWord: (b[3] >> 3) & 0x1F,"
good_r = "\t\tRBits:      (b[3] >> 5) & 0x07,"
good_l = "\t\tLengthWord: b[3] & 0x1F,"
if bad_r in wire_src:
    wire_src = wire_src.replace(bad_r, good_r)
elif good_r not in wire_src:
    raise SystemExit("M1 oracle: RBits line not found in wire.go")
if bad_l in wire_src:
    wire_src = wire_src.replace(bad_l, good_l)
elif good_l not in wire_src:
    raise SystemExit("M1 oracle: LengthWord line not found in wire.go")
wire_path.write_text(wire_src)

dec_path = pathlib.Path("/app/internal/decode/decode.go")
dec_src = dec_path.read_text()
anchor = "\t\tpos += wire.OptionHeaderLen + payloadBytes\n\t\tidx++\n"
if anchor not in dec_src:
    raise SystemExit("M1 oracle: per-option loop tail not found in decode.go")
insertion = (
    "\t\tif oh.RBits != 0 {\n"
    "\t\t\td.Errors = append(d.Errors, Error{\n"
    "\t\t\t\tCode: \"OPT_R_BITS_NONZERO\", Where: \"options\",\n"
    "\t\t\t\tMessage: fmt.Sprintf(\"option %d R=%d, expected 0\", idx, oh.RBits),\n"
    "\t\t\t\tOptIndex: idx,\n"
    "\t\t\t})\n"
    "\t\t}\n"
)
if "OPT_R_BITS_NONZERO" not in dec_src:
    dec_src = dec_src.replace(anchor, insertion + anchor)
    dec_path.write_text(dec_src)
PYEOF

echo "==> verify the patches landed"
grep -n '(b\[3\] >> 5) & 0x07' /app/internal/wire/wire.go
grep -n 'LengthWord: b\[3\] & 0x1F' /app/internal/wire/wire.go
grep -n 'OPT_R_BITS_NONZERO' /app/internal/decode/decode.go

if ! grep -qF '(b[3] >> 5) & 0x07' /app/internal/wire/wire.go; then
    echo "M1 oracle: wire.go RBits fix did not land" >&2
    exit 1
fi
if ! grep -qF 'LengthWord: b[3] & 0x1F' /app/internal/wire/wire.go; then
    echo "M1 oracle: wire.go LengthWord fix did not land" >&2
    exit 1
fi
if ! grep -qF 'OPT_R_BITS_NONZERO' /app/internal/decode/decode.go; then
    echo "M1 oracle: OPT_R_BITS_NONZERO check did not land in decode.go" >&2
    exit 1
fi

echo "==> build and run the unit tests"
mkdir -p /app/bin
go build -o /app/bin/gnvtlv ./cmd/gnvtlv
go build ./...
go test ./internal/wire/... ./internal/decode/...
