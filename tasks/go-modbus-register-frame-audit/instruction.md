# Modbus register capture audit drift

Gateway QA reports the Go register capture auditor under `/app/environment` no longer matches its framing and audit contracts. Rebuilt `/app/bin/registeraudit` runs disagree with independent recomputation from fixture bytes on practice and regression trees: Modbus CRC16 rejects valid frames, merge overlays from `.mregorder` sidecars are ignored, continuation scans seed rolling digests from the wrong durable tip, duplicate collapse keys collide on slave ids instead of sequence ids, checkpoint markers are counted in the chain, slave allow-list rejects are missing, register totals include wrong rows, min/max register bounds reflect the pre-collapse stream, summary JSON is wrapped in a debug envelope instead of the flat report object, and `/app/out/.mregtip` is not refreshed after successful audits.

Repair sources under `/app/environment` so the normal pipeline regenerates `/app/out/mreg_audit.json`. The verifier clears `/app/out`, rebuilds the binary, and reruns audits across fixture directories; hand-written JSON without that pipeline is insufficient. Do not edit `/tests`.

`/app/bin/registeraudit audit -mreg-dir <DIR> -segment <N> -json-out <PATH>`

Rebuild after source edits:

`bash -lc 'go build -C /app/environment -o /app/bin/registeraudit /app/environment/cmd/registeraudit'`

Practice output path: `/app/out/mreg_audit.json`. Merge ordering, framing, chain linkage, continuation seeding, and counting semantics are in `/app/environment/docs/audit_contract.md`; binary frame layout is in `/app/environment/docs/frame_layout.md`. Allowed slave ids are listed in `/app/environment/data/slave_allowlist.txt`. The audit contract also defines processing order: CRC validation, checkpoint removal, segment filter with allow-list reject (before deduplication), duplicate-sequence collapse (last row wins), then chain and summary totals on the collapsed stream.

Required JSON keys are api_version, segment, mreg_files, frame_count, register_read_count, crc_failure_count, exception_count, chain_root_hex, duplicate_seq_drops, slave_reject_count, checkpoint_skip_count, min_reg, max_reg, and active_slave_count. List-valued fields such as `mreg_files` must serialize as JSON arrays; when a scan directory has no `.mreg` capture files, `mreg_files` is an empty array (`[]`), not `null`. Successful audits persist `/app/out/.mregtip` beside the report. Continuation marker files (`.mreg_continue`) change how prior durable output participates in later scans.
