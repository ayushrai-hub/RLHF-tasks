//! Legacy ingest path from an earlier one-step simulate-shot prototype — not on integrate/export hot path.

pub fn legacy_ingest_path() -> &'static str {
    "/app/state/legacy-shot.json"
}
