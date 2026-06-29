"""Key rotation for encrypted Prefect block export files."""

from rotation_coordinator import coordinate_rotation


def rotate_keys(export_path: str, old_key: bytes, new_key: bytes) -> None:
    coordinate_rotation(export_path, old_key, new_key)
