# AES-GCM encryption contract

Cryptographic derivation lives in `key_derivation.py` with helpers in `hkdf_params.py`.
AES-GCM wire format lives in `aes_crypto.py`. **All three modules may require fixes.**

## Per-field HKDF (key_derivation.py)

Public functions: `derive_field_key`, `build_gcm_aad`.

```text
derive_field_key(master_key, field_name, block_type, key_version=1) -> bytes
build_gcm_aad(block_type, field_name, key_version=1) -> bytes
```

Derive a unique 256-bit field key from the master key using HKDF-SHA256.

- Salt input: `config.HKDF_DOMAIN_LABEL`
- Info bytes: UTF-8 encoding of `{block_type}:{field_name}:kv{key_version}`
  (via `derivation_registry.hkdf_info_suffix`). **block_type precedes field_name**
  in the info string even though `derive_field_key` lists `field_name` before
  `block_type` in its parameter list.
- `key_version` defaults to `1` when omitted on derive, encrypt, and decrypt.

The same field name in different block types must produce different derived keys.

## GCM associated data (key_derivation.py)

`build_gcm_aad(block_type, field_name, key_version=1)` must return non-empty
associated data binding the encryption to both the block type and field path.
The same binding is required on decrypt. Encryption and decryption must pass
identical AAD bytes to AES-GCM.

## aes_crypto.py

Public functions: `generate_key`, `encrypt_field`, `decrypt_field`, `encrypt_secrets`, `decrypt_secrets`.

```text
encrypt_field(plaintext, key, field_name, block_type, key_version=1) -> dict
decrypt_field(payload, key, field_name, block_type, key_version=1) -> str
```

- `encrypt_field` returns `nonce` and `ciphertext` hex strings.
- Nonce length: `config.AES_GCM_NONCE_LENGTH`; fresh CSPRNG bytes every call
  (for example `os.urandom` or `secrets.token_bytes` in `crypto_nonce_policy.py`).
  Counter-based or repeating nonce sequences are invalid.
- `encrypt_field` / `decrypt_field` raise `exceptions.KeySizeError` when the
  master key size is not in `config.SUPPORTED_KEY_SIZES`.
- `decrypt_field` raises `exceptions.DecryptionError` on auth failure or
  malformed payloads — never returns an empty string on failure.
- `decrypt_field` must accept the nonce bytes stored in the export payload;
  do not reject decrypt solely because nonce length differs from
  `config.AES_GCM_NONCE_LENGTH` when hex decoding succeeds.

Use flat imports: `from config import ...`, `from exceptions import ...`.
