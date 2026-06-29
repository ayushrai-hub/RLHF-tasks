Add version-aware AES-GCM field encryption and HKDF derivation for sealed exports per /app/docs/crypto-contract.md and /app/docs/derivation-notes.md.

Read /app/docs/overview.md and the crypto docs above. Use /app/config.py and /app/exceptions.py. Per-field keys must bind block type, field path, and export key_version. Nonces must be fresh random bytes on every encrypt call per crypto-contract.md. Preserve existing public function names including `crypto_nonce_policy.next_nonce` and CLI commands from prior milestones.

Acceptance highlights:
- `encrypt_field(plaintext, key, field_name, block_type, key_version=1)` and matching `decrypt_field` argument order; `key_version` defaults to `1`.
- HKDF info bytes are UTF-8 `{block_type}:{field_name}:kv{key_version}` (block type before field path).
- `build_gcm_aad` binds the same block type, field path, and key version on encrypt and decrypt.

Success means this milestone verifier passes.
