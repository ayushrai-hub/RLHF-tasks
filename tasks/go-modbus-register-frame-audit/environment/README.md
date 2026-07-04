# Register capture auditor

Industrial gateway QA ships Modbus register capture shards under fixture trees. The Go auditor rebuilds to `/app/bin/registeraudit` and emits JSON summaries for a target bus segment.

See `docs/audit_contract.md` for report fields and `docs/frame_layout.md` for binary framing.
