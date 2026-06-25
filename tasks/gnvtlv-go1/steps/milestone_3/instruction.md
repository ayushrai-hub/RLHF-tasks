Last piece: `gnvtlv audit` reads the resolved packet plus `audit_policy.json` and decides `ACCEPT` or `DROP`. The current engine handles header strictness and clean packets, but the cascade rules in `/app/docs/CASCADE_RULES.md` aren't wired up. Helpers in `internal/audit/cascade.go` cover §X.2 / §X.3; §X.4 needs its own loop in `audit.Audit` reading the policy's `vendor_allowlist`.

Make `go test ./internal/audit/...` green by:

1. firing §X.2 (`UNKNOWN_CRITICAL`) at packet level — honouring §X.2.1 so a muted rule still flips the decision to `DROP` and sets top-level `override_applied`, AND §X.5 so OAM packets are exempt,
2. firing §X.3 (`MAX_PER_CLASS`) at packet level when an opt_class exceeds the policy cap (strict `>` boundary),
3. firing §X.4 (`EXPERIMENTER_VENDOR_DENIED`) per-option for experimenter-class options whose vendor ID is not in `policy.vendor_allowlist` — read §X.4.1 for the empty-allowlist semantics.

Don't regress the milestone 1 or 2 packages.

```
cd /app && go build -o ./bin/gnvtlv ./cmd/gnvtlv
./bin/gnvtlv audit --in /app/testdata/two_clean.bin
./bin/gnvtlv audit --in /app/testdata/unknown_crit.bin --policy /app/configs/audit_policy.json
./bin/gnvtlv audit --in /app/testdata/unknown_crit.bin --policy /app/configs/audit_policy_muted.json
./bin/gnvtlv audit --in /app/testdata/unknown_noncrit.bin
./bin/gnvtlv audit --in /app/testdata/oam_unknown_crit.bin
./bin/gnvtlv audit --in /app/testdata/oam_clean.bin
./bin/gnvtlv audit --in /app/testdata/two_class_0x0103_boundary.bin --policy /app/configs/audit_policy_capped.json
./bin/gnvtlv audit --in /app/testdata/three_class_0x0103.bin --policy /app/configs/audit_policy_capped.json
./bin/gnvtlv audit --in /app/testdata/two_experimenters.bin --policy /app/configs/audit_policy.json
./bin/gnvtlv audit --in /app/testdata/two_experimenters.bin --policy /app/configs/audit_policy_empty_vendor.json
go test ./...
```
