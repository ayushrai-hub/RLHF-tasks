# Verifier overlay contract

Bundled policy snapshot at /app/data/policies/formation-governance.json.bundled restores overlay policy during extended evaluation.

Pytest seeds bundled overlay inputs from /tests/verifier-fixtures into /opt/verifier-fixtures before grading. Hidden fixtures under /opt/verifier-fixtures/hidden-formation-governance.json and /opt/verifier-fixtures/hidden-hypothesis-priority.json swap formation-governance.json during extended evaluation per verifier-overlay-contract.md. Hidden priority ranks shale-margin-east ahead of copper-belt-north. Hidden guard blocks copper-belt-north versus basalt-deep-west.

The verifier reference helpers reference_load_traces, reference_feed_fingerprint, reference_seq_book, reference_depth_epochs, reference_epoch_fingerprint, reference_voxel_edges, reference_voxel_fingerprint, reference_compose_plan, reference_confidence_margins, reference_margin_table_digest, and reference_chain_fingerprint live in tests/conftest.py and implement the digest math cited in /app/docs/confidence-witness-math.md and survey-ingest-contract.md.

Block profile metadata for copper-belt-north is stored at /app/blocks/copper-belt-north.profile.json for exploration context only.
