# Manifest and integrity seal

Every encrypted export carries a manifest digest and an integrity seal in
metadata. Both are produced during encrypt and must remain consistent through
rotation.

## Secret manifest (secret_manifest.py)

compute_manifest_digest(secret_paths) accepts the list of dot-path secret field
names. Digest is SHA-256 over UTF-8 newline-joined sorted paths. Order of the
input list must not affect the digest.

## Integrity seal (integrity_seal.py + seal_canonical.py)

seal_canonical.canonical_seal_bytes builds deterministic compact JSON for HMAC
input. integrity_seal.py prefixes config.INTEGRITY_HMAC_LABEL before HMAC.

Use only constants already defined in config.py.

### Normative canonical seal payload

canonical_seal_bytes(export) must emit compact sorted JSON with exactly these
top-level keys: metadata (excluding integrity_seal), public, and manifest_digest
as a top-level duplicate of metadata.manifest_digest. secrets and integrity_seal
are excluded.

Decrypt, rotate, and CLI decrypt paths must reject exports whose seal does not
verify after schema validation.

## Replay journal (replay_journal.py)

Sidecar path: {export_path}{config.JOURNAL_SUFFIX}.

Public APIs: journal_path, load_journal, initialize_journal,
record_rotation_commit.

### Normative replay journal schema

Flat JSON object (not a list):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| rotation_seq | integer | yes | Completed rotation count (0 after encrypt) |
| last_key_version | integer | yes | Export key_version after latest update |

load_journal returns {"rotation_seq": 0, "last_key_version": 0} when missing or
invalid.

initialize_journal and record_rotation_commit must persist the journal object as
compact sorted JSON with `separators=(",", ":")` and no insignificant whitespace.

## export_builder.py

Must call build_encrypted_export (do not rename). Preserve CLI argument order:
encrypt block_file output_file key_hex.
