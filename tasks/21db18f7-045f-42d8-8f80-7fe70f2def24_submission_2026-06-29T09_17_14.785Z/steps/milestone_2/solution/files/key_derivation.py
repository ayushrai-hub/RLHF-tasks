"""HKDF key derivation and AES-GCM associated-data construction."""

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from config import HKDF_DOMAIN_LABEL
from hkdf_params import build_aad_bytes, build_hkdf_info


def derive_field_key(
    master_key: bytes, field_name: str, block_type: str, key_version: int = 1
) -> bytes:
    info = build_hkdf_info(block_type, field_name, key_version)
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=HKDF_DOMAIN_LABEL,
        info=info,
    )
    return hkdf.derive(master_key)


def build_gcm_aad(block_type: str, field_name: str, key_version: int = 1) -> bytes:
    return build_aad_bytes(block_type, field_name, key_version)
