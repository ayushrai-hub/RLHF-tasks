# Field classification contract

Before encryption, every block field must be classified as secret or public.
Classification applies to **field path names** (not values).

`field_rules.py` supplies low-level helpers; `block_parser.py` exposes the public API.
**Both modules may require fixes.**

## Nested blocks

Prefect blocks may contain nested mappings. Before classification, nested blocks
must be **flattened** to dot-separated path keys (for example
`connection.auth.password`). The flattening step must skip `block_type_slug`.
Non-mapping values at any depth become leaves in the flat map.

## Secret detection

`field_rules.field_is_secret` must classify dot-path field names using
`config.SECRET_KEYWORD_FRAGMENTS` with case-insensitive fragment matching.
Overrides in the next section always win.

## Public overrides

A path is **never** secret when either holds:

1. The full lowercased path is exactly one of `config.ALWAYS_PUBLIC_FIELDS`, or
2. The lowercased path contains any marker from `config.PUBLIC_OVERRIDE_MARKERS`.

Overrides always win over secret-keyword matches.

## Extraction partition

`extract_secret_fields` and `extract_public_fields` accept a **raw nested block dict**
(not a pre-flattened map). Each function must call `flatten_block` internally before
classifying leaves.

`extract_secret_fields` returns string-valued secret leaves keyed by dot-paths.
`extract_public_fields` returns all other leaves.
Together they must partition every leaf — no overlap.

## Public API (block_parser.py)

These function names are part of the contract:

- `flatten_block`
- `is_secret_field`
- `load_block`
- `validate_block_type`
- `extract_secret_fields`
- `extract_public_fields`
