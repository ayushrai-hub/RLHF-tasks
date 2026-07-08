The arm64 release batch under /app/environment is supposed to reconcile main images, dependent shared objects, and PT_INTERP lineage into one build report, but the shipped sources leave that graph inconsistent. Build specs under /app/environment/fixtures/spec_t2/ carry per-profile link_tag rows, yet emitted link suffixes and transitive shared-object counters diverge from the interpreter table and GNU note payloads. Buffer samples under /app/environment/fixtures/buf_samples/ record tag-check faults for untagged dependents on tagged mains.

Repair sources under /app/environment so /app/tooling/run_h02.sh regenerates /app/output/tag_reconcile.json through its normal harness batch. Rebuild with make -C /app/environment all and run the compiled batch binary.

The JSON carries rows for profiles fw_a and fw_b plus a summary with row_count, batch_stamp tag-v2, and chain_stamp. Every 16 character lowercase hex output field is masked to 48 bits. Each row reports main_digest_hex, dep_digest_hex, lineage_col, so_delta, scan_violations, and fault_obs drawn from the bundled arm64 fixtures, /app/environment/proto/id_map.json, /app/environment/cfg/profile_routes.toml, /app/environment/fixtures/interp_table.toml, buffer samples under /app/environment/fixtures/buf_samples/, and build specs under /app/environment/fixtures/spec_t2/. Output JSON and journal files use UTF-8 encoding.

Note digests are FNV-1a64 over each GNU note payload.

Flags word: the reconciled flags word is the GNU note profile slot byte when interp_table cap_byte matches note byte zero for the active interpreter path, not the cap byte itself.

Lineage column: lineage_col folds the interpreter path digest as its 16-character ASCII hex string, the flags word as four little endian bytes, and a second FNV pass into one hex column.

Scan violations: scan_violations must reflect the transitive shared-object graph walk, not the legacy main-only audit export sealed into /app/work/tag_persist.bin before the graph pass finishes.

Link emit: link emit suffixes must follow each profile build spec dep link_tag. Violation and delta counters reflect dependents whose tag fingerprint diverges from the main image.

Fault observations: fault_obs on both profile rows uses the fw_a buffer sample minus scan_violations, clamped at zero, so fw_b log observations do not drive its row alone when link tags are symmetric. When link tags are asymmetric, fw_b.fault_obs uses fw_b's own raw buffer sample, not the fw_a-adjusted value.

The batch seals graph walk totals into /app/work/tag_persist.bin, appends one tab-separated journal line per profile to /app/work/tag_chain.tsv, then derives chain_stamp from the journal digest. Re-running without edits must leave row fields and chain_stamp unchanged. Deleting only /app/output/tag_reconcile.json and rerunning must recreate the same artifact and journal.
