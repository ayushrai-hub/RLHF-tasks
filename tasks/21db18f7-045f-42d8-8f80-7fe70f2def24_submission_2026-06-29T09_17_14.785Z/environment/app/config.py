"""Configuration constants and defaults for the Prefect secret rotation tool."""

# Supported AES-GCM key sizes (in bits)
SUPPORTED_KEY_SIZES = [128, 192, 256]
DEFAULT_KEY_SIZE = 256

# Nonce length for AES-GCM (bytes)
AES_GCM_NONCE_LENGTH = 12

# Export file schema version
EXPORT_SCHEMA_VERSION = "2.0"

# Case-insensitive substrings that mark a field name as secret-bearing
SECRET_KEYWORD_FRAGMENTS = [
    "key",
    "secret",
    "token",
    "password",
    "pass",
    "credentials",
    "private",
]

# Substrings that force a field name public (override secret keywords)
PUBLIC_OVERRIDE_MARKERS = ["public", "host"]

# Public fields that are never treated as secrets regardless of name
ALWAYS_PUBLIC_FIELDS = ["host", "port", "database", "schema", "region", "endpoint"]

# Staging directory for the two-step encrypt pipeline
STATE_DIR = "/app/state"
BLOCK_STAGING_BASENAME = "block_staging.json"
STAGING_FINGERPRINT_SUFFIX = ".fingerprint"
STAGING_FINGERPRINT_METADATA_KEY = "staging_fingerprint"

# HKDF domain separation label (salt input for per-field derivation)
HKDF_DOMAIN_LABEL = b"prefect-block-secrets-v1"

# HMAC label for export integrity seals
INTEGRITY_HMAC_LABEL = b"prefect-export-integrity-v2"

# Sidecar artifact suffixes for rotation durability
WAL_SUFFIX = ".wal"
EPOCH_SUFFIX = ".epoch"
ROTATION_LOCK_SUFFIX = ".lock"
JOURNAL_SUFFIX = ".journal"

# Stale rotation lock recovery threshold (seconds)
ROTATION_LOCK_STALE_SEC = 120

# Temporary file path used during rotation (must never contain plaintext secrets)
ROTATION_TEMP_PATH = "/tmp/prefect_rotation_temp.json"

# Maximum export file size to load into memory (bytes)
MAX_EXPORT_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Block type identifiers supported by the parser
KNOWN_BLOCK_TYPES = [
    "database-credentials",
    "aws-credentials",
    "gcp-credentials",
    "azure-credentials",
    "secret-block",
    "json-block",
]
