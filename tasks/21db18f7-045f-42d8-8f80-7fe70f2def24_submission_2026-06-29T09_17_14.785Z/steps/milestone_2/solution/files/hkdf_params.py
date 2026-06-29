"""HKDF parameter builders shared by key_derivation."""

from derivation_registry import aad_suffix, hkdf_info_suffix


def build_hkdf_info(block_type: str, field_name: str, key_version: int = 1) -> bytes:
    return hkdf_info_suffix(block_type, field_name, key_version).encode("utf-8")


def build_aad_bytes(block_type: str, field_name: str, key_version: int = 1) -> bytes:
    return aad_suffix(block_type, field_name, key_version).encode("utf-8")
