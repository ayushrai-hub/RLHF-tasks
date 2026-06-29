"""Prefect block YAML parser and secret field detector."""

from typing import Any

import yaml

from field_rules import field_is_public, field_is_secret


def is_secret_field(field_name: str) -> bool:
    if field_is_public(field_name):
        return False
    return field_is_secret(field_name)


def flatten_block(block: dict, prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in block.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(flatten_block(value, path))
        else:
            flat[path] = value
    return flat


def load_block(path: str) -> dict:
    with open(path) as f:
        data = yaml.safe_load(f)
    if data is None:
        return {}
    return data


def validate_block_type(block: dict) -> str:
    return block.get("block_type_slug", "unknown")


def extract_secret_fields(block: dict) -> dict:
    flat = flatten_block(block)
    return {k: v for k, v in flat.items() if is_secret_field(k)}


def extract_public_fields(block: dict) -> dict:
    flat = flatten_block(block)
    return {k: v for k, v in flat.items() if not is_secret_field(k)}
