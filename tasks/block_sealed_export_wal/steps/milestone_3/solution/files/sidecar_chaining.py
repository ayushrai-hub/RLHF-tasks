"""Cross-sidecar invariants enforced before epoch commit."""

from exceptions import IntegrityError


def assert_rotation_sidecars_agree(wal: dict, journal: dict, export_path: str) -> None:
    """WAL completed entries for this export must equal journal.rotation_seq."""
    completed = sum(
        1
        for entry in wal.get("entries", [])
        if entry.get("export_path") == export_path and entry.get("status") == "completed"
    )
    seq = int(journal.get("rotation_seq", 0))
    if completed != seq:
        raise IntegrityError(
            f"WAL completed entries ({completed}) must match journal.rotation_seq ({seq})"
        )
