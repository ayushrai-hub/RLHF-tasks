"""AES-GCM encryption/decryption with per-field key derivation for Prefect block secrets."""

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from config import SUPPORTED_KEY_SIZES
from crypto_nonce_policy import next_nonce
from exceptions import DecryptionError, KeySizeError
from key_derivation import build_gcm_aad, derive_field_key


def generate_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def _validate_key(key: bytes) -> None:
    bits = len(key) * 8
    if bits not in SUPPORTED_KEY_SIZES:
        raise KeySizeError(
            f"Unsupported key size: {bits} bits (allowed: {SUPPORTED_KEY_SIZES})"
        )


def encrypt_field(
    plaintext: str,
    key: bytes,
    field_name: str,
    block_type: str,
    key_version: int = 1,
) -> dict:
    _validate_key(key)
    derived_key = derive_field_key(key, field_name, block_type, key_version)
    aesgcm = AESGCM(derived_key)
    nonce = next_nonce()
    aad = build_gcm_aad(block_type, field_name, key_version)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), aad)
    return {"nonce": nonce.hex(), "ciphertext": ciphertext.hex()}


def decrypt_field(
    encrypted_data: dict,
    key: bytes,
    field_name: str,
    block_type: str,
    key_version: int = 1,
) -> str:
    _validate_key(key)
    try:
        derived_key = derive_field_key(key, field_name, block_type, key_version)
        nonce = bytes.fromhex(encrypted_data["nonce"])
        ciphertext = bytes.fromhex(encrypted_data["ciphertext"])
    except (KeyError, TypeError, ValueError) as exc:
        raise DecryptionError(f"Malformed encrypted payload: {exc}") from exc
    try:
        aesgcm = AESGCM(derived_key)
        aad = build_gcm_aad(block_type, field_name, key_version)
        return aesgcm.decrypt(nonce, ciphertext, aad).decode("utf-8")
    except Exception as exc:
        raise DecryptionError("Authentication tag verification failed") from exc


def encrypt_secrets(
    secrets: dict, key: bytes, block_type: str, key_version: int = 1
) -> dict:
    return {
        field: encrypt_field(value, key, field_name=field, block_type=block_type, key_version=key_version)
        for field, value in secrets.items()
    }


def decrypt_secrets(
    encrypted_secrets: dict, key: bytes, block_type: str, key_version: int = 1
) -> dict:
    return {
        field: decrypt_field(data, key, field_name=field, block_type=block_type, key_version=key_version)
        for field, data in encrypted_secrets.items()
    }
