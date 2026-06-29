# Block YAML loading contract

## load_block(path)

Loads a Prefect block YAML file and returns the parsed top-level mapping.

Must raise `exceptions.BlockParseError` (never a raw `OSError`, `yaml.YAMLError`,
or `TypeError`) when:

- the file cannot be accessed,
- the file size exceeds `config.MAX_EXPORT_FILE_SIZE`,
- the contents are not valid YAML, or
- the parsed result is not a top-level mapping (dict).

On success, returns the parsed dict unchanged.

## validate_block_type(block)

Reads `block_type_slug` from the block mapping.

- Returns the slug unchanged when it is one of `config.KNOWN_BLOCK_TYPES`.
- Raises `exceptions.BlockParseError` when the slug is missing or not in the known list.

Known types: database-credentials, aws-credentials, gcp-credentials,
azure-credentials, secret-block, json-block.

## Sample block fixtures (`/app/sample_blocks/`)

Integration and CLI tests use bundled YAML fixtures. The primary fixture is
`aws_credentials.yaml`:

| Field | Classification | Example value in fixture |
|-------|----------------|--------------------------|
| `block_type_slug` | metadata | `aws-credentials` |
| `region` | public | `us-east-1` |
| `role_arn` | public | `arn:aws:iam::123456789012:role/DataPlatformRole` |
| `aws_access_key_id` | public | `AKIAIOSFODNN7EXAMPLE` |
| `aws_secret_access_key` | secret | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `session_token` | secret | `AQoXnyc4lcK4w9999EXAMPLETOKEN` |

End-to-end encrypt → rotate → decrypt tests assert that `session_token` decrypts
to `AQoXnyc4lcK4w9999EXAMPLETOKEN` after a successful round-trip.
