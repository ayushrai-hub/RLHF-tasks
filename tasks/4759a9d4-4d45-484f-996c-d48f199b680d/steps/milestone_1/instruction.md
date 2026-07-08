# Decode Ceremony Rules

After the March key-ceremony migration, the CSV transparency ledger verifier rejects good rows and accepts forged ones. The signing rules were never captured in one place; they live in `/app/docs/incident_transcript.md`, `/app/docs/ceremony_minutes_addendum.md`, `/app/data/key_rotation_notice.json`, and `/app/docs/api_overview.md`. Earlier bridge notes contradict the ratified council addendum, and the revoked comma-join draft at the top of the transcript must be ignored.

Use `/app/docs/ceremony_rules.template.json` for the exact flat key structure. Populate the remaining empty values by reconciling the ratified addendum, key rotation notice, API overview, and the long incident transcript. Keep the template's pre-filled enum tokens exactly as written — do not paraphrase them from prose. In particular use `bootstrap.algorithm` = `"hmac-sha256"`, `signing.memo_normalization` = `["trim", "collapse_whitespace", "nfc"]`, `chain.row_digest` = `"sha256(canonical|signature_hex)"`, and `chain.link` = `"sha256(prev_digest|row_digest)"`. List the doc paths you relied on in `authoritative_docs`. Write the completed file to `/app/output/ceremony_rules.json` (create `/app/output` if needed).

Run `bash /tests/test.sh` when this part is done.
