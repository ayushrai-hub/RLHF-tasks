"""Version-aware HKDF/GCM context strings for per-field crypto."""


def hkdf_info_suffix(block_type: str, field_name: str, key_version: int) -> str:
    return f"{block_type}:{field_name}:kv{key_version}"


def aad_suffix(block_type: str, field_name: str, key_version: int) -> str:
    return hkdf_info_suffix(block_type, field_name, key_version)
