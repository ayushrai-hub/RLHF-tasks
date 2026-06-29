"""Stage parsed block YAML to an intermediate JSON artifact for export building."""

import json
import os

from block_parser import flatten_block, load_block, validate_block_type
from config import BLOCK_STAGING_BASENAME, STATE_DIR
from staging_lineage import write_fingerprint_sidecar


def stage_block_from_path(block_path: str) -> str:
    block = load_block(block_path)
    slug = validate_block_type(block)
    os.makedirs(STATE_DIR, exist_ok=True)
    staging_path = os.path.join(STATE_DIR, BLOCK_STAGING_BASENAME)
    staging = {"block_type": slug, "fields": flatten_block(block)}
    with open(staging_path, "w") as f:
        json.dump(staging, f, indent=2)
    write_fingerprint_sidecar(staging_path, staging)
    return staging_path
