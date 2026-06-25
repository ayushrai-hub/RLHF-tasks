Supervised stream storm

A bulk data transfer utility fails when run under the bundled service wrapper, while redirecting primary output to disk completes quietly. Logs show truncated failure summaries and write abort on the downstream collector socket during large emission waves. Failures correlate with receive-side recycling mid-transfer rather than application-level rejections.

Fix Go source under `/app/environment`, rebuild `/app/bin/verify-transfer-runs`, and regenerate outputs through the normal pipeline. Wrapper-only changes, hand-written JSON under `/app/output`, or editing tests are insufficient — the verifier reruns the driver and replaces any static report, trace, journal, manifest, sidecar, or ledger files.

Schemas, digest formulas, config merge rules, resume and cache semantics, fixture-pack rules, and build commands are documented in `/app/environment/README.md`. That README is the contract for every field the verifier checks.

The driver writes `/app/output/run_records.json`, `/app/output/ledger_trace.jsonl`, `/app/output/span_journal.jsonl`, `/app/output/run_manifest.jsonl`, `/app/output/run_audit.jsonl`, and persists `/app/output/run_ledger.state` across runs. Run records include fixture_label, writer_epoch, reader_epoch, byte_span, fingerprint, and checkpoint_seal. Ledger trace rows use phase, wave_slice, wave_end, recycle_before, recycle_after, observed, and pending. Span journal entries carry seq, link, observed, and pending. Manifest lines record journal_tail, trace_lines, wave_slices, and manifest_seal. Sidecar rows tie journal_tail, manifest_seal, checkpoint_seal, and audit_seal. The ledger file tracks run_count, prev_audit_tail, and chain_seal. Digest formulas and slice rules for these fields live in the README, including wrap-mode chunk planning from overlay-wins config merge.

Fixture packs live under `/app/data/fixtures/` with stems matching `pack_k*`. Bundled packs such as `pack_k3` and `pack_k5` ship with the image; any additional `pack_k*` JSON added before a run is discovered and included in all outputs on the same terms.

Run the driver as documented in the README.
