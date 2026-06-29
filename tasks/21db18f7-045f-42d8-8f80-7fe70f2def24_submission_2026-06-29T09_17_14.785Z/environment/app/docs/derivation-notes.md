derive_field_key and build_gcm_aad in key_derivation.py derive per-field AES key
material from the master key using HKDF-SHA256. Parameter builders live in
hkdf_params.py; version suffixes live in derivation_registry.py — all three may
require fixes.

Domain separation requirements (all mandatory):

1. HKDF uses `config.HKDF_DOMAIN_LABEL` as the salt input.
2. HKDF info and GCM AAD include block type, field path, and export `key_version`
   via `derivation_registry.hkdf_info_suffix` as `{block_type}:{field_name}:kv{N}`
   (block type first, then field path, then the version suffix). See crypto-contract.md.
3. `aes_crypto.encrypt_secrets` / `decrypt_secrets` must thread the active
   `key_version` from export metadata — never hardcode a fixed epoch after rotation.

`derivation_registry.hkdf_info_suffix(block_type, field_name, key_version)` is the
canonical string builder for both HKDF info and GCM AAD context.

Violating any requirement produces ciphertext that may round-trip locally but
fails cross-version isolation, seal verification, or rotation replay tests.
