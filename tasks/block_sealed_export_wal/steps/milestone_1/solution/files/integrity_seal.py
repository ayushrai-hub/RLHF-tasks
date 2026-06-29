"""HMAC integrity seal over export metadata and public fields."""

import hashlib
import hmac

from config import INTEGRITY_HMAC_LABEL
from seal_canonical import canonical_seal_bytes


def compute_integrity_seal(export: dict, master_key: bytes) -> str:
    message = INTEGRITY_HMAC_LABEL + canonical_seal_bytes(export)
    return hmac.new(master_key, message, hashlib.sha256).hexdigest()


def verify_integrity_seal(export: dict, master_key: bytes) -> bool:
    expected = export.get("metadata", {}).get("integrity_seal")
    if not expected:
        return False
    return hmac.compare_digest(expected, compute_integrity_seal(export, master_key))
